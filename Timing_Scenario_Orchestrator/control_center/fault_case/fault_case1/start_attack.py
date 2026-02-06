#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
调用扰动启动接口（Start Attack Trigger）
@author: GW
"""

import requests
import time


def call_start_interface(
    url="http://192.168.80.200:8080/zh/start",
    timeout=5
):
    print(f"[调用开始] 请求地址: {url}")
    print(f"[调用开始] 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        resp = requests.get(url, timeout=timeout)
        print("[调用结果] HTTP Code:", resp.status_code)
        print("[调用结果] 内容:")
        print(resp.text)
        print("\n[调用结束] 扰动启动指令已发送。\n")

    except Exception as e:
        print("[调用失败] 无法连接到目标接口：")


if __name__ == "__main__":
    call_start_interface()
