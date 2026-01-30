#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-07-01 20:39 
@file: server_control_processor.py
@project: GW_My_tools
@describe: Powered By GW
"""

import socket
import json
import time
import logging
import os
from control_center.utils.send_to_server import send_to_server
from control_center.message.base_message import ServerTrafficControlMessage, ServerPythonCommandMessage
from control_center.utils.logutil import get_logger

logger = get_logger("load_control_center")
SERVER_PORT = 22222
current_dir = os.path.dirname(__file__)  # dispatcher 目录


def send_server_link_limit_config_to_server():
    """
    从 JSON 加载 server_link_limit 配置，并逐台宿主机下发。
    配置文件格式建议：
    {
      "10.0.0.11": [
        {"container":"ausf","direction":"uplink","rate":"5mbit","burst":"1000kbit"},
        {"container":"ausf","direction":"downlink","delay":"200ms","jitter":"50ms","loss":"2%"}
      ],
      "10.0.0.12": [
        {"container":"udm","direction":"downlink","rate":"10mbit"}
      ]
    }
    """
    file_name = "qiantong.json"
    config_path = os.path.join(current_dir, "..", "config", file_name)
    config_path = os.path.abspath(config_path)

    try:
        with open(config_path, "r") as f:
            full_profile = json.load(f)
            logger.info(f"已加载配置文件 {file_name}，目标宿主机数: {len(full_profile)}")
    except Exception as e:
        logger.error(f"配置文件加载失败: {e}")
        return False, {}

    results = {}  # host_ip -> {"ok": bool, "resp": any}

    for host_ip, payload_list in full_profile.items():
        msg = {
            "type": "server_link_limit",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "target_server_ip": host_ip,
            "payload": payload_list
        }

        ok, resp = send_to_server(host_ip, msg)
        results[host_ip] = {"ok": ok, "resp": resp}

        if ok:
            logger.info(f"[server_link_limit] 下发成功: {host_ip}, rules={len(payload_list)}")
        else:
            logger.error(f"[server_link_limit] 下发失败: {host_ip}, resp={resp}")

        time.sleep(1)

    return True, results



def send_traffic_config_to_server():
    # 从 JSON 文件加载所有宿主机配置
    file_name = "server_traffic_profiles.json"
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
        msg = ServerTrafficControlMessage(
            type="server_traffic",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            target_server_ip=host_ip,
            payload=profiles
        )
        send_to_server(host_ip, msg)
        time.sleep(1)


def send_python_cmd_to_server(status_only=False):
    """
    status_only = True → 只执行状态查询，不加载扰动 json，不发送与 ALL 的连接
    """

    file_name = "python_cmd.json"
    config_path = os.path.join(current_dir, "..", "config", file_name)
    config_path = os.path.abspath(config_path)

    try:
        with open(config_path, "r") as f:
            full_profile = json.load(f)
    except Exception as e:
        logger.error(f"配置文件加载失败: {e}")
        return ""

    all_outputs = []

    for host_ip, profiles in full_profile.items():

        # status_only 时，不执行完整命令，只发送状态查询命令
        if status_only:
            # 只取有 "status" 或你默认的第一条命令
            status_payload = [profiles[0]]
            msg = ServerPythonCommandMessage(
                type="exec_python",
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                target_server_ip=host_ip,
                payload=status_payload
            )
        else:
            # 原来完整执行逻辑
            msg = ServerPythonCommandMessage(
                type="exec_python",
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                target_server_ip=host_ip,
                payload=profiles
            )

        ok, resp = send_to_server(host_ip, msg)
        time.sleep(0.3)

        if not ok or not resp:
            continue

        all_outputs.append(resp[0].get("stdout", ""))

    return "\n".join(all_outputs)
