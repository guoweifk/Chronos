#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 16:52 
@file: base_message.py
@project: GW_My_tools
@describe: Powered By GW
"""

from control_center.message.toAgentPayloads.netem import ServerToAgentNetemPayload,AgentNetemPayload
from control_center.message.toAgentPayloads.traffic import ServerToAgentTrafficPayload,AgentTrafficPayload
from control_center.message.serverPayloads.server_traffic import ServerTrafficPayload
from control_center.message.serverPayloads.server_python_cmd import ServerPythonCommandPayload
from dataclasses import dataclass
from typing import Optional,List
from abc import ABC


# server收到的消息
@dataclass
class BaseServerControlMessage(ABC):
    type: str
    timestamp: Optional[str]
    target_server_ip: str


# center发来的控制agent的消息
@dataclass
class AgentNetemControlMessage(BaseServerControlMessage):
    payload: ServerToAgentNetemPayload


# center发来的控制agent的消息
@dataclass
class AgentTrafficControlMessage(BaseServerControlMessage):
    payload: ServerToAgentTrafficPayload


# center发来的控制server的消息
@dataclass
class ServerTrafficControlMessage(BaseServerControlMessage):
    payload: List[ServerTrafficPayload]

@dataclass
class ServerPythonCommandMessage(BaseServerControlMessage):
    payload: List[ServerPythonCommandPayload]


# 发给agent的消息
@dataclass
class BaseAgentControlMessage(ABC):
    type: str
    timestamp: Optional[str]
    target_server_ip: str


@dataclass
class AgentNetemMessage(BaseAgentControlMessage):
    payload: AgentNetemPayload


@dataclass
class AgentTrafficMessage(BaseAgentControlMessage):
    payload: List[AgentTrafficPayload]
