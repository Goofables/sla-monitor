#!/usr/bin/env python3
# @Name: epicfreegame.py
# @Project: monitor
# @Author: Goofables
# @Created: 2022-08-06

import json
from datetime import datetime
from os.path import dirname

import requests

with open(f"{dirname(__file__)}/epicfreegame.json") as f:
    cfg = json.load(f)


def getdate(date: str) -> datetime:
    """datetime object from string"""
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.000Z")


def get_json_list_item(obj: dict, key: str, value: str, target_key: str, default: any = None) -> any:
    """Get the value of target_key from the element of obj where key = value"""
    for item in obj:
        if key in item and item[key] == value:
            if target_key in item:
                return item[target_key]
    return default


response = requests.get(
    "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=US&allowCountries=US",
    headers={"User-Agent": "FreeGameReminder/1.2 (Discord bot by @goofables)", "Accept": "application/json"},
).json()

for game in response["data"]["Catalog"]["searchStore"]["elements"]:
    orig_price = game["price"]["totalPrice"]["fmtPrice"]["originalPrice"]
    if game["price"]["totalPrice"]["originalPrice"] == 0:
        continue
    free = []
    if game["promotions"] is None:
        continue
    for p in game["promotions"]["promotionalOffers"]:
        for promo in p["promotionalOffers"]:
            if (
                promo["discountSetting"]["discountType"] == "PERCENTAGE"
                and promo["discountSetting"]["discountPercentage"] == 0
                and getdate(promo["startDate"]) < datetime.now() < getdate(promo["endDate"])
            ):
                free.append(promo)
    if len(free) == 0:
        continue
    if len(free) > 1:
        print("Multiple free")
        print(json.dumps(free, indent=2))

    key = f"{game['id']}:{free[0]['startDate']}{free[0]['endDate']}"
    if key in cfg["lastrun"]:
        continue
    cfg["lastrun"].append(key)

    # print(json.dumps(response.json(), indent=2))
    image = get_json_list_item(game["keyImages"], "type", "OfferImageWide", "url", "https://i.mxsmp.com/404")
    pageSlug = get_json_list_item(game["catalogNs"]["mappings"], "pageType", "productHome", "pageSlug", "")

    requests.post(
        cfg["webhook"],
        json={
            "content": cfg["content"],
            "embeds": [
                {
                    "title": game["title"],
                    "description": game["description"] + f"\n\n*Previously: ~~{orig_price}~~*",
                    "url": f"https://store.epicgames.com/en-US/p/{pageSlug}",
                    "author": {"name": "Free on epic"},
                    "footer": {"text": "Expires"},
                    "timestamp": free[0]["endDate"],
                    "image": {"url": image},
                }
            ],
            "username": "Epic Freegame",
            "avatar_url": "https://epicgames.com/favicon.ico",
        },
    )

    # If there are multiple and the second fails, dont repost the first
    with open(f"{dirname(__file__)}/epicfreegame.json", "w") as f:
        json.dump(cfg, f)
