#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-28 22:24 
@file: netem_processor.py
@project: GW_My_tools
@describe: Powered By GW
"""
from Network_Impairment_Engine.engine.dispatcher.base_processor import BaseProcessor
import os
import subprocess
import logging
from Network_Impairment_Engine.engine.message.payloads.netem import AgentNetemPayload, AgentNetemDirectionConfig
from Network_Impairment_Engine.engine.message.base_message import AgentNetemMessage
from Network_Impairment_Engine.engine.utils.logutil import get_logger

logger = get_logger("load_control_agent")

logger.info("日志初始化成功")
logger.setLevel(logging.INFO)

SERVER_PORT = 7799
IFACE = os.getenv("NET_IFACE", "eth0")  # 默认使用 eth0，可通过环境变量指定


def run_cmd(cmd):
    logger.info(f"[CMD] {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"[×] 命令执行失败: {e}")


def calc_limit(rate_str, duration_ms=50):
    rate_str = rate_str.lower().replace("bit", "")
    if rate_str.endswith("k"):
        kbps = float(rate_str[:-1])
    elif rate_str.endswith("m"):
        kbps = float(rate_str[:-1]) * 1000
    else:
        kbps = float(rate_str) / 1000
    bytes_per_ms = kbps * 1000 / 8 / 1000
    return int(bytes_per_ms * duration_ms)


def clear_tc():
    run_cmd(f"tc qdisc del dev {IFACE} root || true")
    run_cmd(f"tc qdisc del dev {IFACE} ingress || true")


class NetemProcessor(BaseProcessor):
    def handle(self, msg: AgentNetemMessage):
        self.apply_network_config(msg.payload)

    def apply_egress(self, cfg: AgentNetemDirectionConfig):
        if not cfg or not cfg.rate:
            return

        rate = cfg.rate
        burst = cfg.burst
        limit = cfg.limit

        if not limit:
            limit = calc_limit(rate, duration_ms=50)

        run_cmd(f"tc qdisc add dev {IFACE} root tbf rate {rate} burst {burst} limit {limit}")
        logger.info(f"[↑] 上行限速设置成功: rate={rate}, burst={burst}, limit={limit}")

    def apply_ingress(self, cfg: AgentNetemDirectionConfig):
        if not cfg or not cfg.rate:
            return

        rate = cfg.rate
        burst = cfg.burst
        drop = cfg.drop

        run_cmd(f"tc qdisc add dev {IFACE} handle ffff: ingress")
        action = "drop" if drop else "pass"
        run_cmd(
            f"tc filter add dev {IFACE} parent ffff: protocol ip u32 match u32 0 0 "
            f"police rate {rate} burst {burst} {action}"
        )
        logger.info(f"[↓] 下行限速设置成功: rate={rate}, burst={burst}, drop={drop}")

    def apply_network_config(self, config: AgentNetemPayload):
        if not config.enable:
            logger.info("[ℹ] 收到禁用配置，跳过限速设置")
            clear_tc()
            return

        clear_tc()
        logger.info("[ℹ] 开始egress")
        self.apply_egress(config.egress)
        logger.info("[ℹ] 开始ingress")
        self.apply_ingress(config.ingress)
