#!/usr/bin/env python3

import sys, json

d = json.load(sys.stdin)

dl = d['download']
ul = d['upload']

if isinstance(dl, dict):
    # Ookla CLI (`speedtest --format=json`): bandwidth is bytes/sec.
    download = round(dl['bandwidth'] * 8 / 1_000_000, 2)
    upload   = round(ul['bandwidth'] * 8 / 1_000_000, 2)
    ping     = round(d['ping']['latency'], 1)
    server   = (d['server'].get('location') or d['server'].get('name') or '')
    sponsor  = (d['server'].get('name') or '')
else:
    # Legacy speedtest-cli (`speedtest-cli --json`): download/upload is bits/sec.
    download = round(dl / 1_000_000, 2)
    upload   = round(ul / 1_000_000, 2)
    ping     = round(d['ping'], 1)
    server   = d['server']['name']
    sponsor  = d['server']['sponsor']

server  = server.strip().replace('\n', ' ').replace(',', '')
sponsor = sponsor.strip().replace('\n', ' ').replace(',', '')
print(f"{download}|{upload}|{ping}|{server}|{sponsor}")
