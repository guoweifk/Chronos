#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 17:01 
@file: netem_payload.py
@project: GW_My_tools
@describe: Powered By GW
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class AgentNetemDirectionConfig:
    rate: str = "1mbit"
    burst: str = "10k"
    limit: str = "1mbit"
    drop: bool = True


@dataclass
class AgentNetemPayload:
    egress: AgentNetemDirectionConfig
    ingress: AgentNetemDirectionConfig
    enable: bool = False

@dataclass
class ServerToAgentNetemPayload:
    services: Dict[str, AgentNetemPayload]

    @staticmethod
    def from_dict(d: dict) -> "ServerToAgentNetemPayload":
        return ServerToAgentNetemPayload(
            services={name: AgentNetemPayload(**cfg) for name, cfg in d["services"].items()}
        )