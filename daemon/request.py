#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist
request settings (cookies, auth, proxies).
"""
import base64
from .dictionary import CaseInsensitiveDict, CookieDict


class AuthCredentials:
    """Holds parsed authentication credentials per RFC 2617/7235."""

    def __init__(self, scheme=None, username=None, password=None, realm=None):
        self.scheme = scheme
        self.username = username
        self.password = password
        self.realm = realm
        self.params = {}

    def __repr__(self):
        return f"AuthCredentials(scheme={self.scheme}, username={self.username})"

    @staticmethod
    def from_auth_header(header_value):
        """Parse Authorization header per RFC 2617/7235."""
        creds = AuthCredentials()
        if not header_value:
            return creds

        parts = header_value.split(' ', 1)
        creds.scheme = parts[0].lower()
        if len(parts) > 1:
            params_str = parts[1]

            if creds.scheme == 'basic':
                try:
                    decoded = base64.b64decode(params_str).decode('utf-8')
                    creds.username, creds.password = decoded.split(':', 1)
                except Exception:
                    pass

            else:
                for param in params_str.split(','):
                    if '=' in param:
                        key, val = param.split('=', 1)
                        creds.params[key.strip()] = val.strip().strip('"')
                        if key.strip().lower() == 'realm':
                            creds.realm = val.strip().strip('"')

        return creds

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "_raw_headers",
        "_raw_body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
        "auth",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        #: HTTP path
        self.path = None
        # The cookies set used to create Cookie header
        self.cookies = None
        #: request body to send to the server.
        self.body = None
        # The raw header
        self._raw_headers = None
        #: The raw body
        self._raw_body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None
        #: Authentication credentials parsed from Authorization header
        self.auth = None

    def extract_request_line(self, request):
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()

            if path == '/':
                path = '/index.html'
        except Exception:
            return None, None

        return method, path, version
             
    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val
        return headers

    def fetch_headers_body(self, request):
        """Prepares the given HTTP headers."""
        # Split request into header section and body section
        parts = request.split("\r\n\r\n", 1)  # split once at blank line

        _headers = parts[0]
        _body = parts[1] if len(parts) > 1 else ""
        return _headers, _body

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""

        # Prepare the request line from the request header
        print("[Request] prepare request missg {}".format(request))
        self.method, self.path, self.version = self.extract_request_line(request)
        print("[Request] {} path {} version {}".format(self.method, self.path, self.version))

        # Parse headers from request
        self.headers = self.prepare_headers(request)
        self.headers = self.headers or {}

        # Parse cookies per RFC 6265
        cookie_header = self.headers.get('cookie', '')
        self.cookies = CookieDict.parse_cookie_header(cookie_header)

        # Parse authentication per RFC 2617/7235
        auth_header = self.headers.get('authorization', '')
        self.auth = AuthCredentials.from_auth_header(auth_header)

        #
        # @bksysnet Preapring the webapp hook with AsynapRous instance
        # The default behaviour with HTTP server is empty routed
        #
        # TODO manage the webapp hook in this mounting point
        #

        if routes:
            self.routes = routes
            print("[Request] Routing METHOD {} path {}".format(self.method, self.path))
            self.hook = routes.get((self.method, self.path))
            print("[Request] Hook has request {}".format(request))
            #
            # self.hook manipulation goes here
            # ...
            #

        self._raw_heaers = ""
        self._raw_body = ""

        return

    def prepare_body(self, data, files, json=None):
        self.prepare_content_length(self.body)
        self.body = body
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        return


    def prepare_content_length(self, body):
        self.headers["Content-Length"] = "0"
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        return


    def prepare_auth(self, auth, url=""):
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        return

    def prepare_cookies(self, cookies):
            self.headers["Cookie"] = cookies
