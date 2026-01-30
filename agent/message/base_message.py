#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 16:52 
@file: base_message.py
@project: GW_My_tools
@describe: Powered By GW
"""

from agent.message.payloads.netem import AgentNetemPayload
from agent.message.payloads.traffic import AgentTrafficPayload
from dataclasses import dataclass
from typing import Optional,List
from abc import ABC


@dataclass
class BaseAgentMessage(ABC):
    type: str
    timestamp: Optional[str]


@dataclass
class AgentNetemMessage(BaseAgentMessage):
    payload: AgentNetemPayload

    @staticmethod
    def from_dict(d: dict) -> "AgentNetemMessage":
        return AgentNetemMessage(
            type=d["type"],
            timestamp=d.get("timestamp"),
            payload=AgentNetemPayload.from_dict(d["payload"])
        )


@dataclass
class AgentTrafficMessage(BaseAgentMessage):
    payload: List[AgentTrafficPayload]

    @staticmethod
    def from_dict(d: dict) -> "AgentTrafficMessage":
        return AgentTrafficMessage(
            type=d["type"],
            timestamp=d.get("timestamp"),
            payload=[AgentTrafficPayload.from_dict(item) for item in d["payload"]]
        )



