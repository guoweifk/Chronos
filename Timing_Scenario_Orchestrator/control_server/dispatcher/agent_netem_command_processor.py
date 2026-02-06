#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 21:11 
@file: agent_netem_command_processor.py
@project: GW_My_tools
@describe: Powered By GW
"""
from Timing_Scenario_Orchestrator.control_server.dispatcher.base_processor import BaseProcessor
import os
import logging
from Timing_Scenario_Orchestrator.control_server.message.base_message import AgentNetemControlMessage, AgentNetemMessage
from Timing_Scenario_Orchestrator.control_server.utils.logutil import get_logger
from Timing_Scenario_Orchestrator.control_server.utils import agent_ip_config, send_to_agent
from datetime import datetime

logger = get_logger("load_control_manager")

logger.info("日志初始化成功")
logger.setLevel(logging.INFO)

SERVER_PORT = 7799
IFACE = os.getenv("NET_IFACE", "eth0")  # 默认使用 eth0，可通过环境变量指定


class AgentNetemCommandProcessor(BaseProcessor):

    def handle(self, msg: AgentNetemControlMessage):
        logger.info(f"[→] 收到 拥塞 控制消息，目标服务数量: {len(msg.payload.services)}")
        payload = msg.payload
        service_map = payload.services

        for service_name, service_cfg in service_map.items():
            logger.debug(f"[服务] 准备处理服务: {service_name}")

            # 获取目标 Agent 的 IP
            target_ip = agent_ip_config.get_ip(service_name)
            if not target_ip:
                logger.warning(f"[×] 未找到服务 {service_name} 对应的 agent IP，跳过")
                continue

            # 构造发送消息
            agent_traffic_message = AgentNetemMessage(
                type="agent_netem",
                payload=service_cfg,  # 应为 List[AgentTrafficPayload]
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

            # 发送消息
            success = send_to_agent(target_ip, agent_traffic_message)

            if success:
                logger.info(f"[✓] 成功下发拥塞控制指令到 {service_name} ({target_ip})")
            else:
                logger.error(f"[×] 下发拥塞控制指令失败: {service_name} ({target_ip})")
        return True