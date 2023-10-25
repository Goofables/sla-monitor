#!/usr/bin/env python3
# @Name: main.py
# @Project: monitor/gcp/function_code
# @Author: Goofables
# @Created: 2023-10-18

# Google Cloud Function receiver

import functions_framework

import monitor


@functions_framework.http
def run_checks(*args, **kwargs):
    monitor.run()
    return "OK"
