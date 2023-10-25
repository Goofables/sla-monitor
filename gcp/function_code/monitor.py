#!/usr/bin/env python3
# @Name: monitor.py
# @Project: monitor/gcp/function_code
# @Author: Goofables
# @Created: 2023-10-19

import datetime
import json
import os
import socket
import time

import requests
from google.cloud import bigquery  # pylint: disable=E0401,E0611

with open("config.json", encoding="UTF8") as f:
    cfg = json.load(f)

ERROR_ICON = "https://cdn1.iconfinder.com/data/icons/toolbar-std/512/error-512.png"
GET_SERVICES_QUERY = """
SELECT id, name, owner_discord_id, check_type, check_subject
FROM `sla.services`
ORDER BY name;"""

INSERT_LOG_QUERY = """INSERT INTO `sla.log` (service_id, status, time)
VALUES (@service_id, @status, @time);"""


class ACTIONS:
    """Possible check actions"""

    @staticmethod
    def tcp(address: str) -> bool:
        """Ping a tcp port"""
        try:
            address = address.split(":")
            if len(address) != 2:
                raise ValueError("Wrong address format")
            ip = address[0]
            port = int(address[1])
        except (ValueError, IndexError):
            print(f"Malformed address: {address}")
            return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            r = sock.connect_ex((ip, port))
            sock.close()
        except socket.gaierror:
            return False
        return r == 0

    @staticmethod
    def ping(address: str) -> bool:
        """ICMP ping an address or hostname"""
        return os.system(f"ping -c 1 {address}") == 0

    @staticmethod
    def http(address: str) -> bool:
        """Attempt web connection to address"""
        try:
            resp = requests.get(
                url=address,
                headers={"User-Agent": "Monitor/1.2 (Service status monitor)"},
                timeout=5,
                allow_redirects=False,
            )
        except requests.exceptions.RequestException:
            return False
        return resp.status_code < 400


def run() -> None:
    """Run the checks"""
    notification_data = {
        "content": "",
        "avatar_url": ERROR_ICON,
        "embeds": [
            {
                "title": "Services down: ",
                "description": "",
                "color": 16711680,
                "thumbnail": {"url": ERROR_ICON, "height": 1, "width": 1},
            }
        ],
    }
    down = 0
    client = bigquery.Client()
    for service in client.query(GET_SERVICES_QUERY).result():
        print(f"Running {service['name']}")
        start = time.time()

        action = getattr(ACTIONS, service["check_type"])
        if callable(action):
            try:
                result = action(service["check_subject"])
            except Exception as e:  # pylint: disable=W0718
                print(f"Check error: {service}: {e}")
                result = False
        else:
            print(f"Invalid check type: {service['check_type']}")
            result = False

        client.query(
            INSERT_LOG_QUERY,
            bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("service_id", "INTEGER", service["id"]),
                    bigquery.ScalarQueryParameter("status", "BOOL", result),
                    bigquery.ScalarQueryParameter("time", "TIMESTAMP", datetime.datetime.utcnow()),
                ]
            ),
        )

        if result:
            continue

        down += 1
        notification_data["embeds"][0]["description"] += f"{service['name']}\n"

        if (user := f"<@{service['owner_discord_id']}> ") not in notification_data["content"]:
            notification_data["content"] += user

        print(f"Finished in {time.time()-start}")

    if down == 0:
        return

    notification_data["embeds"][0]["title"] += f"`{down}`"

    requests.post(cfg["webhook"], json=notification_data, timeout=10)


if __name__ == "__main__":
    run()
