#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 17:01 
@file: netem_payload.py
@project: GW_My_tools
@describe: Powered By GW
"""
from typing import Optional
from dataclasses import dataclass


@dataclass
class AgentNetemDirectionConfig:
    rate: str = "1mbit"
    burst: str = "10k"
    limit: str = "1mbit"
    drop: bool = True

    @staticmethod
    def from_dict(d: dict) -> "AgentNetemDirectionConfig":
        return AgentNetemDirectionConfig(
            rate=d.get("rate", "1mbit"),
            burst=d.get("burst", "10k"),
            limit=d.get("limit", "1mbit"),
            drop=d.get("drop", True)
        )


@dataclass
class AgentNetemPayload:
    egress: AgentNetemDirectionConfig
    ingress: AgentNetemDirectionConfig
    enable: bool = False

    @staticmethod
    def from_dict(d: dict) -> "AgentNetemPayload":
        return AgentNetemPayload(
            egress=AgentNetemDirectionConfig.from_dict(d.get("egress", {})),
            ingress=AgentNetemDirectionConfig.from_dict(d.get("ingress", {})),
            enable=d.get("enable", False)
        )
