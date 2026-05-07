#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# AsynapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the AsynapRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""

import argparse
import daemon.backend as backend_module

from apps import create_sampleapp

PORT = 2026  # Default port

if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
    parser.add_argument('--role', choices=['tracker', 'peer'], default=None,
                        help='Start this process as a tracker or a peer node')
    parser.add_argument('--tracker-ip', default='127.0.0.1',
                        help='Tracker IP for peer auth verification and coordination')
    parser.add_argument('--tracker-port', type=int, default=8000,
                        help='Tracker port for peer auth verification and coordination')
    parser.add_argument('--async-mode', choices=['threading', 'callback', 'coroutine'], default='threading',
                        help='Backend communication mode')
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port
    role = args.role if args.role else ('tracker' if port == 8000 else 'peer')
    backend_module.mode_async = args.async_mode

    # Prepare and launch the RESTful application
    create_sampleapp(
        ip,
        port,
        run_role=role,
        tracker_ip=args.tracker_ip,
        tracker_port_value=args.tracker_port,
    )
