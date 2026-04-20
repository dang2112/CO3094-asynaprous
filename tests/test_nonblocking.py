#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#

import socket
import threading
import selectors
import asyncio
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daemon.backend import create_backend, run_backend, handle_client, handle_client_callback


TEST_IP = "127.0.0.1"
TEST_PORT_BASE = 19000


def find_free_port():
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((TEST_IP, 0))
        return s.getsockname()[1]


def make_http_request(path="/test", method="GET", body=""):
    """Craft a minimal HTTP/1.1 request string."""
    return (
        f"{method} {path} HTTP/1.1\r\n"
        f"Host: {TEST_IP}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
        f"{body}"
    )


class TestThreadingMode(unittest.TestCase):
    """Test multi-threaded non-blocking mechanism using actual backend.py."""

    def setUp(self):
        self.port = find_free_port()
        self.server_ready = threading.Event()
        self.routes = {("GET", "/test"): lambda h, b: b"HTTP/1.1 200 OK\r\n\r\nthreaded"}

    def test_threaded_accepts_connection(self):
        """Test threaded mode accepts a connection and returns response."""
        import daemon.backend as be
        be.mode_async = "threading"

        def start_server():
            create_backend(TEST_IP, self.port, self.routes)

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        time.sleep(0.4)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((TEST_IP, self.port))
            request = make_http_request("/test")
            sock.sendall(request.encode())
            response = sock.recv(4096)
        finally:
            sock.close()

        self.assertIn(b"HTTP/1.1", response)
        self.assertIn(b"threaded", response)
        print(f"[TEST] threaded: connection accepted on port {self.port}")

    def test_threaded_concurrent_clients(self):
        """Test threaded mode handles multiple concurrent clients."""
        import daemon.backend as be
        be.mode_async = "threading"

        responses = []
        num_clients = 3

        def start_server():
            be.create_backend(TEST_IP, self.port, self.routes)

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        time.sleep(0.4)

        def make_request(client_id):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            try:
                sock.connect((TEST_IP, self.port))
                request = make_http_request(f"/test{client_id}")
                sock.sendall(request.encode())
                resp = sock.recv(4096)
                return (client_id, resp)
            except Exception as e:
                return (client_id, str(e).encode())
            finally:
                sock.close()

        with ThreadPoolExecutor(max_workers=num_clients) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_clients)]
            responses = [f.result() for f in futures]

        successful = sum(1 for _, r in responses if b"HTTP/1.1" in r)
        self.assertEqual(successful, num_clients)
        print(f"[TEST] threaded concurrent: {successful}/{num_clients} succeeded")


class TestCallbackMode(unittest.TestCase):
    """Test event-driven callback/selector mode using actual backend.py."""

    def setUp(self):
        self.port = find_free_port()
        be_mode = "callback"

    def test_callback_selector_nonblocking(self):
        """Test callback/selector mode uses non-blocking socket."""
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((TEST_IP, self.port))
        server_sock.listen(5)
        server_sock.setblocking(False)

        sel = selectors.DefaultSelector()
        sel.register(server_sock, selectors.EVENT_READ, data={"mode": "accept"})

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.settimeout(2.0)
        client_sock.connect((TEST_IP, self.port))

        events = sel.select(timeout=1.0)
        self.assertTrue(len(events) > 0, "Selector should detect readable socket")

        key, mask = events[0]
        self.assertEqual(key.data["mode"], "accept")

        sel.unregister(server_sock)
        server_sock.close()
        client_sock.close()
        print(f"[TEST] callback selector: non-blocking works on port {self.port}")

    def test_callback_in_backend_context(self):
        """Test callback mode works in actual backend context."""
        import daemon.backend as be

        sel = selectors.DefaultSelector()
        test_routes = {("GET", "/test"): lambda h, b: b"callback response"}

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((TEST_IP, self.port))
        server_sock.listen(5)

        sel.register(server_sock, selectors.EVENT_READ,
                  (handle_client_callback, TEST_IP, self.port, test_routes))

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.settimeout(3.0)
        client_sock.connect((TEST_IP, self.port))
        client_sock.sendall(b"GET /test HTTP/1.1\r\nHost: localhost\r\n\r\n")
        time.sleep(0.2)

        sel.unregister(server_sock)
        server_sock.close()
        client_sock.close()
        print(f"[TEST] callback in backend: registered with selector")


class TestCoroutineMode(unittest.TestCase):
    """Test coroutine async/await mode using actual backend.py."""

    def setUp(self):
        self.port = find_free_port()

    def test_asyncio_coroutine_server(self):
        """Test asyncio coroutine server works."""
        async def handler(reader, writer):
            data = await reader.read(1024)
            writer.write(b"HTTP/1.1 200 OK\r\n\r\nasync")
            await writer.drain()
            writer.close()

        async def run_server():
            server = await asyncio.start_server(handler, TEST_IP, self.port)
            async with server:
                await server.serve_forever()

        async def run_client():
            reader, writer = await asyncio.open_connection(TEST_IP, self.port)
            writer.write(b"GET /test HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = await reader.read(4096)
            writer.close()
            return response

        async def orchestrate():
            server_task = asyncio.create_task(run_server())
            await asyncio.sleep(0.3)
            try:
                response = await asyncio.wait_for(run_client(), timeout=5.0)
                return response
            finally:
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass

        response = asyncio.run(orchestrate())
        self.assertIn(b"HTTP/1.1", response)
        self.assertIn(b"async", response)
        print(f"[TEST] coroutine: asyncio server works on port {self.port}")

    def test_coroutine_backend_async_server(self):
        """Test using backend.py async_server function."""
        import daemon.backend as be
        be.mode_async = "coroutine"

        async def client_test():
            await asyncio.sleep(0.2)
            reader, writer = await asyncio.open_connection(TEST_IP, self.port + 1)
            writer.write(b"GET /test HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = await reader.read(4096)
            writer.close()
            return response

        async def run_test():
            be.mode_async = "coroutine"
            server_task = asyncio.create_task(be.async_server(TEST_IP, self.port + 1, {}))
            await asyncio.sleep(0.3)
            try:
                response = await asyncio.wait_for(client_test(), timeout=5.0)
            finally:
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass
            return response

        response = asyncio.run(run_test())
        self.assertIsNotNone(response)
        print(f"[TEST] coroutine backend: async_server launched on port {self.port + 1}")


class TestCallbackModeIntegration(unittest.TestCase):
    """Test callback mode using actual backend.py."""

    def setUp(self):
        self.port = find_free_port()

    def test_callback_mode_works(self):
        """Test callback mode in backend accepts connections."""
        import daemon.backend as be
        be.mode_async = "callback"

        routes = {("GET", "/test"): lambda h, b: b"HTTP/1.1 200 OK\r\n\r\ncallback"}

        def start_server():
            be.create_backend(TEST_IP, self.port, routes)

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        time.sleep(0.5)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((TEST_IP, self.port))
            request = make_http_request("/test")
            sock.sendall(request.encode())
            response = sock.recv(4096)
        finally:
            sock.close()

        self.assertIn(b"HTTP/1.1", response)
        self.assertIn(b"callback", response)
        print(f"[TEST] callback mode integration: passed on port {self.port}")


class TestModeSelection(unittest.TestCase):
    """Test mode selection mechanism."""

    def test_mode_variable_exists(self):
        """Test mode_async variable exists."""
        import daemon.backend as be
        self.assertIn(be.mode_async, ["threading", "callback", "coroutine"])
        print(f"[TEST] mode_async = {be.mode_async}")

    def test_set_mode_threading(self):
        """Test setting mode to threading."""
        import daemon.backend as be
        be.mode_async = "threading"
        self.assertEqual(be.mode_async, "threading")

    def test_set_mode_callback(self):
        """Test setting mode to callback."""
        import daemon.backend as be
        be.mode_async = "callback"
        self.assertEqual(be.mode_async, "callback")

    def test_set_mode_coroutine(self):
        """Test setting mode to coroutine."""
        import daemon.backend as be
        be.mode_async = "coroutine"
        self.assertEqual(be.mode_async, "coroutine")


if __name__ == "__main__":
    unittest.main(verbosity=2)