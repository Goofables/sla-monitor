#!/usr/bin/env python3
# @Name: monitor.py
# @Project: monitor
# @Author: Goofables
# @Created: 2019-06-20

import json
import os
import socket
import time

import requests


def tcp(ip: str, port: int) -> bool:
    """Ping a tcp port"""
    print(f"Pinging {ip} {port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        r = sock.connect_ex((ip, port))
        sock.close()
    except socket.gaierror:
        return False
    return r == 0


def ping(address: str) -> bool:
    """ICMP ping an address or hostname"""
    return os.system(f"ping -c 1 {address}") == 0


def web(address: str) -> bool:
    """Attempt web connection to address"""
    print(f"Web {address}")
    try:
        resp = requests.get(
            url=address,
            headers={"User-Agent": "Monitor/1.2 (Service status monitor)"},
            timeout=5,
            allow_redirects=False,
        )
    except requests.exceptions.ReadTimeout:
        return False
    return resp.status_code < 400


services = {
    "mc": {
        lambda: tcp("1.2.3.4", 25565): "error",
    },
    "web": {
        lambda: web("https://example.com"): "warning",
    },
    "icmp": {
        lambda: ping("10.0.0.100"): "error",
    },
}

WEBHOOK_URL = "https://discordapp.com/api/webhooks/"

# pylint: disable=C0301
ICONS = {
    "info": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Info_icon-72a7cf.svg/1024px-Info_icon-72a7cf.svg.png",
    "warning": "https://cdn2.iconfinder.com/data/icons/color-svg-vector-icons-2/512/warning_alert_attention_search-512.png",
    "error": "https://cdn1.iconfinder.com/data/icons/toolbar-std/512/error-512.png",
}
# pylint: enable=C0301

data = {"content": "", "avatar_url": ICONS["error"], "embeds": []}
error = False
for service, actions in services.items():
    print(f"Runing {service}")
    start = time.time()
    for action, icon in actions.items():
        if action():
            continue
        embed = {
            "title": service,
            "description": "Could not connect",
            "color": 16711680,
            "thumbnail": {"url": ICONS[icon], "height": 1, "width": 1},
        }
        # https://discordapp.com/developers/docs/resources/channel#embed-object
        data["embeds"].append(embed)
        if icon == "error":
            error = True
    print(f"Finished {len(actions)} in {time.time()-start}")

if len(data["embeds"]) == 0:
    exit(0)

if error:
    data["content"] = "<@you>"

result = requests.post(WEBHOOK_URL, data=json.dumps(data), headers={"Content-Type": "application/json"})
# print(json.dumps(data))
exit(len(data["embeds"]))
