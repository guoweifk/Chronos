#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: LX
@time: 2025-06-23 18:25 
@file: load_control_agent.py
@project: GW_My_tools
@describe: Powered By LX
"""

import socket
import json
from Network_Impairment_Engine.engine.dispatcher.message_dispatcher import AgentMessageDispatcher
import os
import sys

# 把 engine 上一层（）加入 sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # control_server/
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # docker_open5gs/
sys.path.insert(0, PROJECT_ROOT)

from Network_Impairment_Engine.engine.utils.logutil import get_logger

logger = get_logger("load_control_agent")

SERVER_PORT = 7799
IFACE = os.getenv("NET_IFACE", "eth0")  # 默认使用 eth0，可通过环境变量指定
logger.info(f"PROJECT_ROOT {PROJECT_ROOT}")

def start_agent():
    dispatcher = AgentMessageDispatcher()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(('0.0.0.0', SERVER_PORT))
        server_socket.listen(5)
        logger.info(f"[启动] Agent 监听端口 {SERVER_PORT}")

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                with client_socket:
                    raw_data = client_socket.recv(65535)
                    logger.info(f"[数据] 接收到来自 {client_address[0]} 的原始数据")

                    if raw_data:
                        message = json.loads(raw_data.decode())
                        logger.info(f"msg:" + raw_data.decode())
                        dispatcher.dispatch(message)
                    else:
                        logger.warning("[!] 空消息")
            except Exception as e:
                logger.error(f"[×] 处理异常: {e}")


if __name__ == "__main__":
    start_agent()

# 创建
#  tc qdisc add dev eth0 handle ffff: ingress
#  tc filter add dev eth0 parent ffff: protocol ip u32 match u32 0 0 police rate 100kbit burst 10k drop
#  tc qdisc add dev eth0 root tbf rate 100kbit burst 10kbit limit 50K


# 修改
#  tc qdisc replace dev eth0 root tbf rate 200kbit burst 1280b latency 50ms
#  tc filter replace dev eth0 parent ffff: protocol ip u32 match u32 0 0 police rate 2000kbit burst 100k drop
