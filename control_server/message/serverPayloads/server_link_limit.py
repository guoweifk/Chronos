#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2026-01-04
@file: server_link_limit.py
@project: GW_My_tools
@describe: Server side link rate limit payload (container-based)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ServerLinkLimitPayload:
    container: str
    direction: str          # uplink | downlink
    rate: Optional[str] = None   # 带宽限制（可选）
    burst: Optional[str] = None

    # ===== 新增：链路劣化参数 =====
    delay: Optional[str] = None      # e.g. "100ms"
    jitter: Optional[str] = None     # e.g. "20ms"
    loss: Optional[str] = None       # e.g. "1%"
    duplicate: Optional[str] = None  # e.g. "0.5%"
    reorder: Optional[str] = None    # e.g. "25%"
    reorder_corr: Optional[str] = None  # e.g. "50%"

    @staticmethod
    def from_dict(d: dict) -> "ServerLinkLimitPayload":
        return ServerLinkLimitPayload(
            container=d["container"],
            direction=d["direction"],
            rate=d.get("rate"),
            burst=d.get("burst"),
            delay=d.get("delay"),
            jitter=d.get("jitter"),
            loss=d.get("loss"),
            duplicate=d.get("duplicate"),
            reorder=d.get("reorder"),
            reorder_corr=d.get("reorder_corr"),
        )

