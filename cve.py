#!/usr/bin/env python3
# @Name: cve.py
# @Project: monitor
# @Author: Goofables
# @Created: 2021-12-16
"""
https://services.nvd.nist.gov/rest/json/cves/1.0/?pubStartDate=2021-12-15T23:00:00:000%20UTC&pubEndDate=2021-12-16T01:00:00:000%20UTC
"""
import json
from datetime import datetime
from os.path import dirname

import requests

dir = dirname(__file__)
cfg = json.load(open(dir + "/cve.json"))
start = datetime.utcnow().replace(microsecond=0).isoformat() + ":000 UTC"
resp = requests.get(
    "https://services.nvd.nist.gov/rest/json/cves/1.0/?modStartDate={}&modEndDate={}".format(cfg["last"], start)
)
# resp = requests.get("https://services.nvd.nist.gov/rest/json/cve/1.0/CVE-2021-38759")
cfg["last"] = start
if resp.status_code != 200:
    print("Error " + str(resp.status_code))
    exit(1)
resp = resp.json()
if resp["totalResults"] == 0:
    exit(0)


def get_criticality(cvss: float):
    if cvss > 8.9:
        return cvss, "Critical", 11141375
    elif cvss > 6.9:
        return cvss, "High", 16711680
    elif cvss > 3.9:
        return cvss, "Medium", 16746496
    else:
        return cvss, "Low", 16776960


for cve in resp["result"]["CVE_Items"]:
    ID = cve["cve"]["CVE_data_meta"]["ID"]
    try:
        try:
            criticality = get_criticality(float(cve["impact"]["baseMetricV3"]["cvssV3"]["baseScore"]))
        except:
            continue
        desc = ""
        for d in cve["cve"]["description"]["description_data"]:
            if d["lang"] == "en":
                desc = d["value"]
        message = {
            "title": ID,
            "description": desc + "\n\n_" + cve["impact"]["baseMetricV3"]["cvssV3"]["vectorString"] + "_",
            "url": "https://nvd.nist.gov/vuln/detail/" + ID,
            "color": criticality[2],
            "fields": [],
            "author": {"name": str(criticality[0]) + " - " + criticality[1]},
            "footer": {"text": "Assigned by " + cve["cve"]["CVE_data_meta"]["ASSIGNER"]},
            "timestamp": cve["publishedDate"],
        }
        print(cve["publishedDate"])
        cpe = ""
        for node in cve.get("configurations", {}).get("nodes", []):
            for cpe_match in node.get("cpe_match", []):
                if cpe_match["vulnerable"]:
                    full_cpe = cpe_match["cpe23Uri"]
                    while full_cpe[-2:] == ":*":
                        full_cpe = full_cpe[:-2]
                    cpe += "`" + full_cpe + "`"
                    if "versionEndIncluding" in cpe_match:
                        cpe += " <= " + cpe_match["versionEndIncluding"]
                    cpe += "\n"
        if len(cpe) > 0:
            message["fields"].append({"name": "CPE", "value": cpe})
        refs = ""
        for ref in cve["cve"]["references"]["reference_data"]:
            name = ref["name"]
            for a in ["https://", "http://"]:
                name = name.replace(a, "")
            refs += "[" + name + "](" + ref["url"] + ")\n"
        message["fields"].append(
            {
                "name": "References",
                "value": refs + "\n"
                "[CVE Details](https://www.cvedetails.com/cve/{0}) | "
                "[Google](https://www.google.com/search?q={0}) | "
                "[Github](https://github.com/search?q={0}) | "
                "[Twitter](https://twitter.com/#!/search/realtime/{0}) | "
                "[Youtube](https://www.youtube.com/results?search_query={0}) ".format(ID),
            }
        )
        requests.post(cfg["webhook"] + "?wait=true", json={"embeds": [message]})
    except:
        print("Failed: " + ID)
        print(json.dumps(cve, indent=4))

json.dump(cfg, open(dir + "/cve.json", "w"))
