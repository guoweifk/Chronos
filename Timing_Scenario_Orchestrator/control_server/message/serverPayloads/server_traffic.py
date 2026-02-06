#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 23:13 
@file: server_traffic.py
@project: GW_My_tools
@describe: Powered By GW
"""
from dataclasses import dataclass


@dataclass
class ServerTrafficPayload:
    target_cf: str
    target_port: str
    action: str
    rate: str = "500kbit"
    count: int = 1000
    interval: float = 0.01

    @staticmethod
    def from_dict(d: dict) -> "ServerTrafficPayload":
        return ServerTrafficPayload(
            target_cf=d["target_cf"],
            target_port=str(d["target_port"]),
            action=d["action"],
            rate=d.get("rate", "500kbit"),
            count=int(d.get("count", 1000)),
            interval=float(d.get("interval", 0.01))
        )