# import json
# import urllib.parse
# import re
# from daemon.asynaprous import AsynapRous

# app = AsynapRous()

# active_peers = {}
# chat_channels = {"general": []}

# def parse_data(headers, body):
#     """Hàm thông minh: Ưu tiên đọc Body, nếu Body rớt mạng thì móc từ Headers"""
#     data = {}
#     # 1. Thử đọc từ Body truyền thống
#     if body:
#         try:
#             body_str = body.decode('utf-8') if isinstance(body, bytes) else body
#             data = json.loads(body_str)
#         except Exception:
#             pass
    
#     # 2. Đọc cứu hộ từ Headers (Bypass lỗi cắt gói tin của framework)
#     if not data:
#         if isinstance(headers, dict): 
#             for k, v in headers.items():
#                 if k.lower().startswith('x-chat-'):
#                     data[k[7:].lower()] = urllib.parse.unquote(str(v))
#         elif isinstance(headers, str): 
#             matches = re.findall(r'(?i)X-Chat-([^:]+):\s*([^\r\n]+)', headers)
#             for k, v in matches:
#                 data[k.lower()] = urllib.parse.unquote(v.strip())
#     return data

# # ==========================================
# # GIAI ĐOẠN CLIENT-SERVER (TRACKER)
# # ==========================================
# @app.route('/submit-info', methods=['POST'])
# def submit_info(headers="guest", body="anonymous"):
#     data = parse_data(headers, body)
#     username = data.get('username')
    
#     if username:
#         active_peers[username] = {"ip": data.get('ip', '127.0.0.1'), "port": data.get('port')}
#         return {"message": "Registered successfully"}
        
#     return {"error": "Missing username"}

# @app.route('/get-list', methods=['GET'])
# def get_list(headers="guest", body="anonymous"):
#     return active_peers

# # ==========================================
# # GIAI ĐOẠN PEER-TO-PEER (P2P)
# # ==========================================
# @app.route('/send-peer', methods=['POST'])
# def send_peer(headers="guest", body="anonymous"):
#     data = parse_data(headers, body)
#     channel = data.get('channel', 'general')
#     if channel not in chat_channels:
#         chat_channels[channel] = []
        
#     chat_channels[channel].append({
#         "from": data.get('sender', 'Unknown'),
#         "text": data.get('message', ''),
#         "timestamp": data.get('timestamp', '')
#     })
#     return {"message": "Message received"}

# @app.route('/get-messages', methods=['GET'])
# def get_messages(headers="guest", body="anonymous"):
#     return chat_channels

# def create_sampleapp(ip, port):
#     print(f"=====================================")
#     print(f"🚀 Node P2P đang chạy tại {ip}:{port}")
#     print(f"=====================================")
#     app.prepare_address(ip, port)
#     app.run()

import json
import os
from daemon.asynaprous import AsynapRous

app = AsynapRous()

active_peers = {}
chat_channels = {"general": [], "study-group": []}

def parse_body(body):
    if not body: return {}
    try:
        body_str = str(body).strip()
        if not body_str: return {}
        return json.loads(body_str)
    except Exception as e:
        print(f"❌ [CẢNH BÁO] Lỗi đọc JSON: {e}. Dữ liệu gốc: {body}")
        return {}

@app.route('/chat.html', methods=['GET'])
def serve_ui(headers, body):
    with open(os.path.join('www', 'chat.html'), 'r', encoding='utf-8') as f: return f.read()

@app.route('/static/js/chat.js', methods=['GET'])
def serve_js(headers, body):
    with open(os.path.join('static', 'js', 'chat.js'), 'r', encoding='utf-8') as f: return f.read()

@app.route('/submit-info', methods=['POST', 'OPTIONS'])
def submit_info(headers, body):
    data = parse_body(body)
    if data.get('username'):
        active_peers[data['username']] = {"ip": data.get('ip', '127.0.0.1'), "port": data['port']}
        print(f"✅ [TRACKER] {data['username']} đã Online!")
        return {"msg": "Đăng ký thành công"}
    return {"error": "Thiếu username"}

@app.route('/get-list', methods=['GET', 'OPTIONS'])
def get_list(headers, body):
    return active_peers

@app.route('/send-peer', methods=['POST', 'OPTIONS'])
def send_peer(headers, body):
    data = parse_body(body)
    if not data: return {"msg": "Preflight OK"} 
    
    channel = data.get('channel', 'general')
    if channel not in chat_channels: chat_channels[channel] = []
    
    # Radar theo dõi tin nhắn: In thật to ra Terminal!
    print(f"💬 [P2P RECEIVER] Có tin nhắn từ '{data.get('sender')}' vào kênh #{channel}: {data.get('message')}")
    
    chat_channels[channel].append({
        "from": data.get('sender', 'Unknown'),
        "text": data.get('message', ''),
        "timestamp": data.get('timestamp', '')
    })
    return {"msg": "Đã nhận"}

@app.route('/get-messages', methods=['GET', 'OPTIONS'])
def get_messages(headers, body):
    return chat_channels

def create_sampleapp(ip, port):
    print(f"🚀 WebApp Node đang chạy tại {ip}:{port}")
    app.prepare_address(ip, port)
    app.run()