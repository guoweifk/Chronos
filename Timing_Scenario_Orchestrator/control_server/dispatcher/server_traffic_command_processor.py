#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 21:44 
@file: server_traffic_command_processor.py
@project: GW_My_tools
@describe: Powered By GW
"""
from Timing_Scenario_Orchestrator.control_server.dispatcher.base_processor import BaseProcessor
import os
import logging
from Timing_Scenario_Orchestrator.control_server.message.base_message import ServerTrafficControlMessage
import multiprocessing
from typing import Dict
from Timing_Scenario_Orchestrator.control_server.utils.logutil import get_logger
from Timing_Scenario_Orchestrator.control_server.utils.traffic_workker import traffic_worker
from Timing_Scenario_Orchestrator.control_server.utils import agent_ip_config

logger = get_logger("load_control_manager")

logger.info("日志初始化成功")
logger.setLevel(logging.INFO)

SERVER_PORT = 7799
IFACE = os.getenv("NET_IFACE", "eth0")  # 默认使用 eth0，可通过环境变量指定


class ServerTrafficCommandProcessor(BaseProcessor):
    def __init__(self):
        # 存储多个目标对应的流量进程
        self.process_map: Dict[str, multiprocessing.Process] = {}

    def handle(self, msg: ServerTrafficControlMessage):

        payload_list = msg.payload
        if not isinstance(payload_list, list):
            logger.error("payload 应为列表形式")
            return

        for payload in payload_list:

            action = payload.action
            target_cf = payload.target_cf
            target_ip = agent_ip_config.get_ip(target_cf)
            target_port = payload.target_port
            key = f"{target_ip}:{target_port}"

            if action == "start":
                if key in self.process_map and self.process_map[key].is_alive():
                    logger.warning(f"流量生成已在运行中，目标: {key}，忽略新启动请求")
                    return

                rate = payload.rate
                count = payload.count
                interval = payload.interval

                proc = multiprocessing.Process(
                    target=traffic_worker,
                    args=(target_ip, target_port, rate, count, interval)
                )
                proc.start()
                self.process_map[key] = proc
                logger.info(f"[+] 启动流量进程 -> {key}")

            elif action == "stop":
                proc = self.process_map.get(key)
                if proc and proc.is_alive():
                    proc.terminate()
                    proc.join()
                    del self.process_map[key]
                    logger.info(f"[-] 停止流量进程 -> {key}")
                else:
                    logger.warning(f"[×] 无运行中的流量进程可停止 -> {key}")
            elif action == "stop_all":
                logger.info("[!] 收到停止所有流量进程请求")
                keys_to_stop = list(self.process_map.keys())
                for k in keys_to_stop:
                    proc = self.process_map.get(k)
                    if proc and proc.is_alive():
                        proc.terminate()
                        proc.join()
                        logger.info(f"[-] 停止流量进程 -> {k}")
                    self.process_map.pop(k, None)

            else:
                logger.warning(f"[×] 未知流量控制动作: {action}")
        return True