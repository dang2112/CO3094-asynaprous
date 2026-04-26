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

from collections.abc import MutableMapping
import secrets
import time


class CaseInsensitiveDict(MutableMapping):
    """The :class:`CaseInsensitiveDict<MutableMapping>` object, which 
    contains a custom behavior of MutuableMapping.

    Usage::

      >>> import tools
      >>> word = CaseInsensitiveDict(status_code='404', msg="Not found")
      >>> code = word['status_code']
      >>> code 
      404

      >>> msg = word['msg']
      >>> s.send(r)
      Not found

      >>> print(word)
      {'status_code': '404', 'msg': 'Not found'}

    """

    def __init__(self, *args, **kwargs):
        self.store = {k.lower(): v for k, v in dict(*args, **kwargs).items()}

    def __getitem__(self, key):
        return self.store[key.lower()]

    def __setitem__(self, key, value):
        self.store[key.lower()] = value

    def __delitem__(self, key):
        del self.store[key.lower()]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)


class CookieDict(CaseInsensitiveDict):
    """Cookie dictionary per RFC 6265.

    Handles Set-Cookie header parsing and building.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._flags = []

    def parse_set_cookie(self, header_value):
        """Parse a Set-Cookie header value per RFC 6265."""
        parts = header_value.split(';')
        name_value = parts[0].split('=', 1)
        if len(name_value) != 2:
            return
        self[name_value[0].strip()] = name_value[1].strip()

        for part in parts[1:]:
            part = part.strip()
            if '=' in part:
                attr, val = part.split('=', 1)
                self[attr.lower()] = val.strip('"')
            else:
                self._flags.append(part.lower())

    def build_set_cookie_header(self, name, value, path=None, domain=None,
                                max_age=None, secure=False, http_only=False):
        """Build a Set-Cookie header value per RFC 6265."""
        parts = [f"{name}={value}"]
        if path:
            parts.append(f"Path={path}")
        if domain:
            parts.append(f"Domain={domain}")
        if max_age is not None:
            parts.append(f"Max-Age={max_age}")
        if secure:
            parts.append("Secure")
        if http_only:
            parts.append("HttpOnly")
        return "; ".join(parts)

    def to_header_string(self):
        """Build Cookie header string for requests."""
        return "; ".join(f"{k}={v}" for k, v in self.store.items())

    @staticmethod
    def parse_cookie_header(header_value):
        """Parse Cookie header per RFC 6265 into dict."""
        cookies = {}
        if not header_value:
            return cookies
        for pair in header_value.split(';'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                cookies[k.strip()] = v.strip()
        return cookies