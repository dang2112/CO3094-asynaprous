import http.client
import json
import os

from daemon.asynaprous import AsynapRous
from daemon.request import AuthCredentials

tracker_app = AsynapRous()
peer_app = AsynapRous()

# Tracker state
active_peers = {}
channel_members = {"general": []}
chat_channels = {"general": []}
user_credentials = {}
active_sessions = {}

# Peer state
peer_chat_channels = {"general": []}

role = "peer"
tracker_host = "127.0.0.1"
tracker_port = 8000


def configure_runtime(run_role="peer", tracker_ip="127.0.0.1", tracker_port_value=8000):
    global role, tracker_host, tracker_port
    role = run_role
    tracker_host = tracker_ip
    tracker_port = int(tracker_port_value)


def get_channel_members(channel):
    if channel == "general":
        return list(active_peers.keys())
    return channel_members.get(channel, [])


def store_message(message_store, data):
    channel = data.get("channel", "general")
    if channel not in message_store:
        message_store[channel] = []

    message_store[channel].append(
        {
            "from": data.get("sender", "Unknown"),
            "text": data.get("message", ""),
            "timestamp": data.get("timestamp", ""),
        }
    )
    return channel


def parse_body(body):
    if not body:
        return {}
    try:
        body_str = str(body).strip()
        if not body_str:
            return {}
        return json.loads(body_str)
    except Exception as exc:
        print(f"[WARN] Failed to parse JSON body: {exc}. Raw body: {body}")
        return {}


def unauthorized(message="Unauthorized"):
    return 401, {"error": message}


def forbidden(message="Forbidden"):
    return 403, {"error": message}


def bad_request(message):
    return 400, {"error": message}


def extract_bearer_token(header_value):
    parts = header_value.split(" ", 1)
    if len(parts) != 2:
        return None
    return parts[1].strip()


def resolve_authenticated_user(headers):
    auth_header = headers.get("authorization", "")
    creds = AuthCredentials.from_auth_header(auth_header)

    if creds.scheme == "basic" and creds.username:
        stored_password = user_credentials.get(creds.username)
        if stored_password and stored_password == creds.password:
            return creds.username
        return None

    if creds.scheme == "bearer":
        token = extract_bearer_token(auth_header)
        if not token:
            return None
        for username, active_token in active_sessions.items():
            if active_token == token:
                return username

    return None


def require_tracker_auth(headers, expected_username=None):
    username = resolve_authenticated_user(headers)
    if not username:
        return None, unauthorized("Authentication required")

    if expected_username and username != expected_username:
        return None, forbidden("Authenticated user does not match request user")

    return username, None


def verify_auth_with_tracker(headers, expected_username=None):
    auth_header = headers.get("authorization", "")
    if not auth_header:
        return None, unauthorized("Authentication required")

    payload = {}
    if expected_username:
        payload["username"] = expected_username

    try:
        conn = http.client.HTTPConnection(tracker_host, int(tracker_port), timeout=3)
        conn.request(
            "POST",
            "/verify-auth",
            body=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "Authorization": auth_header,
            },
        )
        response = conn.getresponse()
        raw_body = response.read().decode("utf-8", errors="ignore")
        conn.close()
    except Exception:
        return None, (503, {"error": "Tracker authentication service unavailable"})

    try:
        result = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        result = {"error": "Invalid tracker auth response"}

    if response.status != 200 or not result.get("valid"):
        status_code = response.status if response.status != 200 else 401
        return None, (status_code, {"error": result.get("error", "Authentication failed")})

    return result.get("username"), None


def fetch_tracker_json(path, auth_header="", method="GET", payload=None):
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload)
    else:
        body = None

    conn = http.client.HTTPConnection(tracker_host, int(tracker_port), timeout=3)
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        raw_body = response.read().decode("utf-8", errors="ignore")
    finally:
        conn.close()

    try:
        parsed = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        parsed = {"error": "Invalid tracker response"}

    return response.status, parsed


def send_message_to_peer(ip, port, payload, extra_headers=None):
    try:
        conn = http.client.HTTPConnection(ip, int(port), timeout=3)
        body = json.dumps(payload)
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        conn.request("POST", "/send-peer", body=body, headers=headers)
        response = conn.getresponse()
        text = response.read().decode("utf-8", errors="ignore")
        conn.close()
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = text
        return True, {"status": response.status, "body": parsed}
    except Exception as exc:
        return False, str(exc)


def remove_inactive_peer(username):
    active_peers.pop(username, None)
    active_sessions.pop(username, None)
    for members in channel_members.values():
        if username in members:
            members.remove(username)


def fanout_message_to_members(members, payload):
    results = {}
    failed_peers = []

    for peer_name in members:
        if peer_name not in active_peers:
            continue

        peer_info = active_peers[peer_name]
        ok, result = send_message_to_peer(
            peer_info["ip"],
            peer_info["port"],
            payload,
            extra_headers={"X-Tracker-Relay": "1"},
        )
        results[peer_name] = {"ok": ok, "detail": result}

        if not ok:
            failed_peers.append(peer_name)

    for peer_name in failed_peers:
        remove_inactive_peer(peer_name)

    return results


@tracker_app.route("/register", methods=["POST", "OPTIONS"])
def register(headers, body):
    data = parse_body(body)
    if not data or not data.get("username") or not data.get("password"):
        return bad_request("Missing username or password")

    username = data["username"]
    if username in user_credentials:
        return 409, {"error": "Username already exists"}

    user_credentials[username] = data["password"]
    print(f"[TRACKER] Registered account: {username}")
    return {"msg": "Registration successful"}


@tracker_app.route("/login", methods=["POST", "OPTIONS"])
def login(headers, body):
    data = parse_body(body)
    if not data or not data.get("username"):
        return bad_request("Missing username")

    username = data["username"]
    password = data.get("password", "")

    stored_password = user_credentials.get(username)
    if not stored_password or stored_password != password:
        return unauthorized("Invalid username or password")

    import time

    token = f"{username}_{int(time.time())}"
    active_sessions[username] = token
    active_peers[username] = {"ip": data.get("ip", "127.0.0.1"), "port": data["port"]}

    if username not in channel_members.get("general", []):
        channel_members.setdefault("general", []).append(username)

    print(f"[TRACKER] {username} logged in and is online")
    return {"msg": "Login successful", "token": token}


@tracker_app.route("/verify-auth", methods=["POST", "OPTIONS"])
def verify_auth(headers, body):
    data = parse_body(body)
    expected_username = data.get("username") if isinstance(data, dict) else None
    username, auth_error = require_tracker_auth(headers, expected_username=expected_username)
    if auth_error:
        status_code, payload = auth_error
        return status_code, {"valid": False, **payload}

    return {"valid": True, "username": username}


@tracker_app.route("/submit-info", methods=["POST", "OPTIONS"])
def submit_info(headers, body):
    data = parse_body(body)
    if not data or not data.get("username") or not data.get("port"):
        return bad_request("Missing username or port")

    _, auth_error = require_tracker_auth(headers, expected_username=data["username"])
    if auth_error:
        return auth_error

    username = data["username"]
    active_peers[username] = {"ip": data.get("ip", "127.0.0.1"), "port": data["port"]}
    if username not in channel_members.get("general", []):
        channel_members.setdefault("general", []).append(username)
    return {"msg": "Peer info updated"}


@tracker_app.route("/logout", methods=["POST", "OPTIONS"])
def logout(headers, body):
    data = parse_body(body)
    username = data.get("username")
    if not username:
        return bad_request("Missing username")

    _, auth_error = require_tracker_auth(headers, expected_username=username)
    if auth_error:
        return auth_error

    if username in active_peers or username in active_sessions:
        remove_inactive_peer(username)
        print(f"[TRACKER] {username} logged out")

    return {"msg": "Logout successful"}


@tracker_app.route("/chat.html", methods=["GET"])
def serve_ui(headers, body):
    with open(os.path.join("www", "chat.html"), "r", encoding="utf-8") as file_handle:
        return file_handle.read()


@tracker_app.route("/static/js/chat.js", methods=["GET"])
def serve_js(headers, body):
    with open(os.path.join("static", "js", "chat.js"), "r", encoding="utf-8") as file_handle:
        return file_handle.read()


@peer_app.route("/chat.html", methods=["GET"])
def peer_serve_ui(headers, body):
    with open(os.path.join("www", "chat.html"), "r", encoding="utf-8") as file_handle:
        return file_handle.read()


@peer_app.route("/static/js/chat.js", methods=["GET"])
def peer_serve_js(headers, body):
    with open(os.path.join("static", "js", "chat.js"), "r", encoding="utf-8") as file_handle:
        return file_handle.read()


@tracker_app.route("/create-channel", methods=["POST", "OPTIONS"])
def create_channel(headers, body):
    data = parse_body(body)
    if not data or not data.get("channel_name"):
        return bad_request("Missing channel name")

    creator = data.get("creator") or data.get("username")
    creator, auth_error = require_tracker_auth(headers, expected_username=creator)
    if auth_error:
        return auth_error

    channel_name = data["channel_name"]
    if channel_name in chat_channels:
        return 409, {"error": "Channel already exists"}

    chat_channels[channel_name] = []
    channel_members[channel_name] = list(dict.fromkeys(data.get("members", []) + [creator]))
    print(f"[TRACKER] Created channel: {channel_name}")
    return {"msg": "Channel created", "channel": channel_name}


@tracker_app.route("/join-channel", methods=["POST", "OPTIONS"])
def join_channel(headers, body):
    data = parse_body(body)
    if not data or not data.get("channel") or not data.get("username"):
        return bad_request("Missing channel or username")

    requester = data.get("requester") or data["username"]
    _, auth_error = require_tracker_auth(headers, expected_username=requester)
    if auth_error:
        return auth_error

    channel = data["channel"]
    username = data["username"]

    if channel not in channel_members:
        return 404, {"error": "Channel does not exist"}

    if username not in channel_members[channel]:
        channel_members[channel].append(username)
        print(f"[TRACKER] {username} joined channel {channel}")

    return {"msg": "Joined channel"}


@tracker_app.route("/add-list", methods=["POST", "OPTIONS"])
def add_list(headers, body):
    return join_channel(headers, body)


@tracker_app.route("/get-channels", methods=["GET", "OPTIONS"])
def get_channels(headers, body):
    _, auth_error = require_tracker_auth(headers)
    if auth_error:
        return auth_error

    members = {channel: get_channel_members(channel) for channel in chat_channels.keys()}
    members["general"] = list(active_peers.keys())

    return {"channels": list(chat_channels.keys()), "members": members}


@peer_app.route("/send-peer", methods=["POST", "OPTIONS"])
def peer_send_peer(headers, body):
    data = parse_body(body)
    if not data:
        return {"msg": "Preflight OK"}

    if headers.get("x-tracker-relay") != "1":
        _, auth_error = verify_auth_with_tracker(headers, expected_username=data.get("sender"))
        if auth_error:
            return auth_error

    channel = store_message(peer_chat_channels, data)
    print(f"[PEER] Message from '{data.get('sender')}' in #{channel}: {data.get('message')}")
    return {"msg": "Received"}


@peer_app.route("/get-messages", methods=["GET", "OPTIONS"])
def peer_get_messages(headers, body):
    _, auth_error = verify_auth_with_tracker(headers)
    if auth_error:
        return auth_error

    return peer_chat_channels


@peer_app.route("/broadcast-peer", methods=["POST", "OPTIONS"])
def peer_broadcast_peer(headers, body):
    data = parse_body(body)
    if not data:
        return {"msg": "Preflight OK"}

    sender, auth_error = verify_auth_with_tracker(headers, expected_username=data.get("sender"))
    if auth_error:
        return auth_error

    message = data.get("message", "")
    channel = data.get("channel", "general")
    timestamp = data.get("timestamp") or ""
    if not message:
        return bad_request("Missing message")

    auth_header = headers.get("authorization", "")
    status_code, channel_data = fetch_tracker_json("/get-channels", auth_header=auth_header)
    if status_code != 200:
        return status_code, channel_data if isinstance(channel_data, dict) else {"error": "Unable to load channels"}

    members = (channel_data.get("members") or {}).get(channel, [])
    if sender not in members:
        return forbidden("Sender is not a member of this channel")

    status_code, peer_data = fetch_tracker_json("/get-list", auth_header=auth_header)
    if status_code != 200:
        return status_code, peer_data if isinstance(peer_data, dict) else {"error": "Unable to load peer list"}

    payload = {
        "sender": sender,
        "message": message,
        "channel": channel,
        "timestamp": timestamp,
    }

    results = {}
    for peer_name in members:
        peer_info = peer_data.get(peer_name)
        if not peer_info:
            continue

        if peer_name == sender:
            store_message(peer_chat_channels, payload)
            results[peer_name] = {"ok": True, "detail": {"status": 200, "body": {"msg": "Stored locally"}}}
            continue

        ok, result = send_message_to_peer(
            peer_info["ip"],
            peer_info["port"],
            payload,
            extra_headers={"Authorization": auth_header},
        )
        results[peer_name] = {"ok": ok, "detail": result}

    return {
        "msg": f"Broadcast sent to {len(results)} peers in channel {channel}",
        "broadcasted_to": len(results),
        "results": results,
    }


@tracker_app.route("/broadcast", methods=["POST", "OPTIONS"])
def broadcast(headers, body):
    data = parse_body(body)
    if not data:
        return {"msg": "Preflight OK"}

    sender = data.get("sender", "Unknown")
    message = data.get("message", "")
    channel = data.get("channel", "general")
    timestamp = data.get("timestamp") or ""

    _, auth_error = require_tracker_auth(headers, expected_username=sender)
    if auth_error:
        return auth_error

    if not message:
        return bad_request("Missing message")

    members = get_channel_members(channel)
    if sender not in members:
        return forbidden("Sender is not a member of this channel")

    payload = {
        "sender": sender,
        "message": message,
        "channel": channel,
        "timestamp": timestamp,
    }

    results = fanout_message_to_members(members, payload)

    print(f"[TRACKER] Broadcast from '{sender}' in #{channel} to {len(results)} members: {message}")
    return {
        "msg": f"Broadcast sent to {len(results)} peers in channel {channel}",
        "broadcasted_to": len(results),
        "results": results,
    }


@tracker_app.route("/broadcast-peer", methods=["POST", "OPTIONS"])
def broadcast_peer(headers, body):
    return broadcast(headers, body)


@tracker_app.route("/connect-peer", methods=["POST", "OPTIONS"])
def connect_peer(headers, body):
    _, auth_error = require_tracker_auth(headers)
    if auth_error:
        return auth_error

    data = parse_body(body)
    username = data.get("username")
    if not username:
        return bad_request("Missing username")

    peer_info = active_peers.get(username)
    if not peer_info:
        return 404, {"error": "Peer not found"}

    return {"peer": {"username": username, **peer_info}}


@tracker_app.route("/get-list", methods=["GET", "OPTIONS"])
def get_list(headers, body):
    _, auth_error = require_tracker_auth(headers)
    if auth_error:
        return auth_error

    return active_peers


def create_sampleapp(ip, port, run_role="peer", tracker_ip="127.0.0.1", tracker_port_value=8000):
    configure_runtime(run_role=run_role, tracker_ip=tracker_ip, tracker_port_value=tracker_port_value)
    app = tracker_app if run_role == "tracker" else peer_app
    print(f"[BOOT] Starting {run_role.upper()} node at {ip}:{port} with tracker {tracker_host}:{tracker_port}")
    app.prepare_address(ip, port)
    app.run()
