#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 17:23 
@file: traffic.py
@project: GW_My_tools
@describe: Powered By GW
"""

from dataclasses import dataclass


@dataclass
class AgentTrafficPayload:
    target_ip: str
    target_port: str
    action: str
    rate: str = "500kbit"
    count: int = 1000
    interval: float = 0.01

    @staticmethod
    def from_dict(d: dict) -> "AgentTrafficPayload":
        return AgentTrafficPayload(
            target_ip=d["target_ip"],
            target_port=d["target_port"],
            action=d["action"],
            rate=d.get("rate", "500kbit"),
            count=d.get("count", 1000),
            interval=d.get("interval", 0.01)
        )
# {
#   "type": "traffic",
#   "payload": {
#     "action": "start",
#     "target_ip": "192.168.0.11",
#     "target_port": 9000,
#     "rate": "500kbit",
#     "count": 1000,
#     "interval": 0.01
#   }
# }
