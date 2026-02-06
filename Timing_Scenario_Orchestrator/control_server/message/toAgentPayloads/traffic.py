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
from typing import Dict,List

@dataclass
class AgentTrafficPayload:
    target_ip: str
    target_port: str
    action: str
    rate: str = "500kbit"
    count: int = 1000
    interval: float = 0.01


@dataclass
class ServerToAgentTrafficPayload:
    services: Dict[str, List[AgentTrafficPayload]]

    @classmethod
    def from_dict(cls, param: dict) -> "ServerToAgentTrafficPayload":
        services_dict = param.get("services", {})
        result = {}

        for service_name, payload_list in services_dict.items():
            result[service_name] = [AgentTrafficPayload(**item) for item in payload_list]

        return cls(services=result)

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
