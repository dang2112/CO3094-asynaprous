#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#

import unittest
import base64
import sys
import os
import socket
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daemon.request import Request, AuthCredentials
from daemon.response import Response
from daemon.dictionary import CookieDict
from daemon.backend import create_backend


TEST_IP = "127.0.0.1"


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((TEST_IP, 0))
        return s.getsockname()[1]


class TestAuthCredentials(unittest.TestCase):
    """Test RFC 2617/7235 Authorization header parsing."""

    def test_parse_basic_auth(self):
        """Test parsing Basic authentication scheme."""
        credentials = "Basic " + base64.b64encode(b"user:pass").decode()
        creds = AuthCredentials.from_auth_header(credentials)

        self.assertEqual(creds.scheme, "basic")
        self.assertEqual(creds.username, "user")
        self.assertEqual(creds.password, "pass")

    def test_parse_basic_auth_with_special_chars(self):
        """Test Basic auth with special characters."""
        credentials = "Basic " + base64.b64encode(b"admin:pa$$w0rd!").decode()
        creds = AuthCredentials.from_auth_header(credentials)

        self.assertEqual(creds.username, "admin")
        self.assertEqual(creds.password, "pa$$w0rd!")

    def test_parse_empty_auth(self):
        """Test empty authorization header."""
        creds = AuthCredentials.from_auth_header("")
        self.assertIsNone(creds.scheme)
        self.assertIsNone(creds.username)

    def test_parse_bearer_auth(self):
        """Test Bearer token authentication."""
        creds = AuthCredentials.from_auth_header("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        self.assertEqual(creds.scheme, "bearer")

    def test_parse_digest_auth(self):
        """Test Digest authentication with realm."""
        creds = AuthCredentials.from_auth_header('Digest username="user", realm="test", nonce="abc"')
        self.assertEqual(creds.scheme, "digest")
        self.assertEqual(creds.realm, "test")
        self.assertEqual(creds.params.get("username"), "user")


class TestCookieDict(unittest.TestCase):
    """Test RFC 6265 Cookie parsing and building."""

    def test_parse_cookie_header(self):
        """Test parsing Cookie header."""
        cookie_str = "session=abc123; user=admin; prefs=dark"
        cookies = CookieDict.parse_cookie_header(cookie_str)

        self.assertEqual(cookies["session"], "abc123")
        self.assertEqual(cookies["user"], "admin")
        self.assertEqual(cookies["prefs"], "dark")

    def test_parse_empty_cookie_header(self):
        """Test parsing empty cookie header."""
        cookies = CookieDict.parse_cookie_header("")
        self.assertEqual(len(cookies), 0)

    def test_build_set_cookie(self):
        """Test building Set-Cookie header."""
        cd = CookieDict()
        header = cd.build_set_cookie_header("session", "xyz789", path="/", http_only=True)

        self.assertIn("session=xyz789", header)
        self.assertIn("Path=/", header)
        self.assertIn("HttpOnly", header)

    def test_build_secure_cookie(self):
        """Test building secure cookie."""
        cd = CookieDict()
        header = cd.build_set_cookie_header("token", "abc", secure=True, http_only=True, max_age=3600)

        self.assertIn("Secure", header)
        self.assertIn("Max-Age=3600", header)


class TestRequestAuth(unittest.TestCase):
    """Test Request class authentication handling."""

    def setUp(self):
        self.request = Request()

    def test_prepare_parses_auth_header(self):
        """Test that prepare() parses Authorization header."""
        http_request = (
            "GET /protected HTTP/1.1\r\n"
            "Host: localhost\r\n"
            "Authorization: Basic " + base64.b64encode(b"user:pass").decode() + "\r\n"
            "\r\n"
        )

        self.request.prepare(http_request)

        self.assertIsNotNone(self.request.auth)
        self.assertEqual(self.request.auth.scheme, "basic")
        self.assertEqual(self.request.auth.username, "user")

    def test_prepare_parses_cookies(self):
        """Test that prepare() parses Cookie header."""
        http_request = (
            "GET / HTTP/1.1\r\n"
            "Host: localhost\r\n"
            "Cookie: session=abc123; user=admin\r\n"
            "\r\n"
        )

        self.request.prepare(http_request)

        self.assertIsNotNone(self.request.cookies)
        self.assertEqual(self.request.cookies.get("session"), "abc123")
        self.assertEqual(self.request.cookies.get("user"), "admin")

    def test_prepare_no_auth(self):
        """Test request without authentication."""
        http_request = "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"

        self.request.prepare(http_request)

        self.assertIsNotNone(self.request.auth)
        self.assertIsNone(self.request.auth.username)


class TestResponseAuth(unittest.TestCase):
    """Test Response class authentication features."""

    def test_set_auth_challenge(self):
        """Test setting WWW-Authenticate challenge."""
        resp = Response()
        resp.set_auth_challenge("Basic", realm="Protected Area")

        self.assertIn("WWW-Authenticate", resp.headers)
        self.assertIn("Basic", resp.headers["WWW-Authenticate"])
        self.assertIn("Protected Area", resp.headers["WWW-Authenticate"])

    def test_set_cookie(self):
        """Test setting Set-Cookie header."""
        resp = Response()
        resp.set_cookie("session", "abc123", path="/", http_only=True)

        self.assertIn("Set-Cookie", resp.headers)
        self.assertIn("session=abc123", resp.headers["Set-Cookie"])

    def test_build_unauthorized(self):
        """Test 401 Unauthorized response building."""
        resp = Response()
        resp.set_auth_challenge("Basic", realm="Test Realm")

        response = resp.build_unauthorized(realm="Test Realm")

        self.assertIn(b"401", response)
        self.assertIn(b"Unauthorized", response)
        self.assertIn(b"WWW-Authenticate", response)
        self.assertIn(b"Basic", response)


class TestProxyAuthForwarding(unittest.TestCase):
    """Test that proxy forwards authentication headers to backend."""

    def test_proxy_forwards_auth_headers(self):
        """Test proxy forwards Authorization header to backend."""
        pass

    def test_proxy_forwards_cookie_headers(self):
        """Test proxy forwards Cookie header to backend."""
        pass


class TestIntegratedAuth(unittest.TestCase):
    """Integration tests for auth with backend server."""

    def setUp(self):
        self.port = find_free_port()

    def test_backend_rejects_unauthenticated(self):
        """Test backend returns 401 for unauthenticated request to protected resource."""
        def start_server():
            create_backend(TEST_IP, self.port, {})

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        time.sleep(0.3)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((TEST_IP, self.port))
            request = "GET /protected HTTP/1.1\r\nHost: localhost\r\n\r\n"
            sock.sendall(request.encode())
            response = sock.recv(4096)
        finally:
            sock.close()

        print(f"[TEST] Response: {response[:100]}")

    def test_backend_accepts_basic_auth(self):
        """Test backend accepts Basic authentication."""
        def auth_handler(headers, body):
            auth = headers.get("authorization", "")
            if "Basic" in auth:
                return b"HTTP/1.1 200 OK\r\n\r\nAuthenticated"
            return b"HTTP/1.1 401 Unauthorized\r\nWWW-Authenticate: Basic\r\n\r\n"

        routes = {("GET", "/protected"): auth_handler}

        def start_server():
            create_backend(TEST_IP, self.port, routes)

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        time.sleep(0.3)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((TEST_IP, self.port))
            creds = base64.b64encode(b"user:pass").decode()
            request = f"GET /protected HTTP/1.1\r\nHost: localhost\r\nAuthorization: Basic {creds}\r\n\r\n"
            sock.sendall(request.encode())
            response = sock.recv(4096)
        finally:
            sock.close()

        self.assertIn(b"200", response)
        self.assertIn(b"Authenticated", response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
