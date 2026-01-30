#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-07-01 20:38 
@file: agent_control_processor.py
@project: GW_My_tools
@describe: Powered By GW
"""

import socket
import json
import time,os
from control_center.utils.send_to_server import send_to_server
from control_center.message.base_message import AgentNetemControlMessage,AgentTrafficControlMessage
from control_center.utils.logutil import get_logger
current_dir = os.path.dirname(__file__)  # dispatcher 目录
logger = get_logger("load_control_center")

SERVER_PORT = 22222
def send_traffic_config_to_agent():
    file_name = "traffic_profiles.json"
    config_path = os.path.join(current_dir, "..", "config", file_name)
    config_path = os.path.abspath(config_path)  # 获取绝对路径
    # 从 JSON 文件加载所有宿主机配置
    try:
        with open(config_path, "r") as f:
            full_profile = json.load(f)
            logger.info(f"已加载配置文件 {file_name}，目标宿主机数: {len(full_profile)}")
    except Exception as e:
        logger.error(f"配置文件加载失败: {e}")
        exit(1)
    for host_ip, profiles in full_profile.items():
        msg = AgentTrafficControlMessage(
            type="agent_traffic",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            target_server_ip=host_ip,
            payload=profiles
        )
        send_to_server(host_ip, msg)
        time.sleep(1)

def send_netem_config_to_agent(file_name):
    # 从 JSON 文件加载所有宿主机配置
    file_name = "free5gc_netem_profiles.json"
    config_path = os.path.join(current_dir, "..", "config", file_name)
    config_path = os.path.abspath(config_path)  # 获取绝对路径
    try:
        with open(config_path, "r") as f:
            full_profile = json.load(f)
            logger.info(f"已加载配置文件 {file_name}，目标宿主机数: {len(full_profile)}")
    except Exception as e:
        logger.error(f"配置文件加载失败: {e}")
        exit(1)

    for host_ip, profiles in full_profile.items():
        msg = AgentNetemControlMessage(
            type="agent_netem",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            target_server_ip=host_ip,
            payload=profiles
        )
        send_to_server(host_ip, msg)
        time.sleep(1)