#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(__file__))

from apps.sampleapp import parse_body

print('Testing parse_body function...')
test_data = '{"sender":"alice","message":"hello","channel":"general"}'
result = parse_body(test_data)
print('Result:', result)

# Test broadcast endpoint logic
print('\nTesting broadcast logic...')
active_peers = {"alice": {"ip": "127.0.0.1", "port": "9001"}, "bob": {"ip": "127.0.0.1", "port": "9002"}}
channel_members = {"general": ["alice", "bob"], "study-group": ["alice"]}

channel = "general"
sender = "alice"
members = channel_members.get(channel, list(active_peers.keys()))
print(f'Channel: {channel}, Members: {members}')

peers_to_broadcast = [p for p in members if p != sender and p in active_peers]
print(f'Peers to broadcast to: {peers_to_broadcast}')