#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-07-01 18:36 
@file: server_python_cmd.py
@project: GW_My_tools
@describe: Powered By GW
"""
from dataclasses import dataclass


@dataclass
class ServerPythonCommandPayload:
    command: str
    time_out:int

    @staticmethod
    def from_dict(d: dict) -> "ServerPythonCommandPayload":
        return ServerPythonCommandPayload(
            command=d["command"],
            time_out=d["time_out"]
        )
