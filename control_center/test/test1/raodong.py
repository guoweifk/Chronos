#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-11-19 14:51 
@file: raodong.py
@project: GW_My_tools
@describe: Powered By GW
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

def main():
    url = "http://192.168.80.200:8080/zh/start"

    try:
        resp = requests.get(url, timeout=5)
        print("Status Code:", resp.status_code)
        print("Response:", resp.text)
    except Exception as e:
        print("Request error:", e)

if __name__ == "__main__":
    main()