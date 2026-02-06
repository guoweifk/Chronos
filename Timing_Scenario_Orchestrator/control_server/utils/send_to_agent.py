#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-30 10:33 
@file: send_to_agent.py
@project: GW_My_tools
@describe: Powered By GW
"""
import socket
import json
from Timing_Scenario_Orchestrator.control_server.utils.logutil import get_logger

AGENT_PORT = 7799  # Agent 监听端口，可根据实际修改

logger = get_logger("load_control_manager")

def send_to_agent(agent_ip: str, message_obj) -> bool:
    try:
        # 将 dataclass 转为 JSON 字符串
        json_data = json.dumps(message_obj, default=lambda o: o.__dict__)
        logger.debug(f"[→] 发送至 {agent_ip}:{AGENT_PORT}，内容: {json_data}")

        with socket.create_connection((agent_ip, AGENT_PORT), timeout=3) as sock:
            sock.sendall(json_data.encode())
        logger.info(f"[✓] 成功发送消息到 agent {agent_ip}")
        return True

    except Exception as e:
        logger.error(f"[×] 发送消息到 agent {agent_ip} 失败: {e}")
        return False
