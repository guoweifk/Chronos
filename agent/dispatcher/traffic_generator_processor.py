#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 16:36 
@file: traffic_generator_processor.py
@project: GW_My_tools
@describe: Powered By GW
"""
from agent.dispatcher.base_processor import BaseProcessor
import multiprocessing
from typing import Dict
from agent.utils.logutil import get_logger
from agent.utils.traffic_worker import traffic_worker
from agent.message.base_message import AgentTrafficMessage, AgentTrafficPayload

logger = get_logger("load_control_agent")


# 启动一个流量发送线程，放到多线程集中，如果要关闭，关闭对应线程
class TrafficGeneratorProcessor(BaseProcessor):
    def __init__(self):
        # 存储多个目标对应的流量进程
        self.process_map: Dict[str, multiprocessing.Process] = {}

    def handle(self, msg: AgentTrafficMessage):

        payload_list = msg.payload
        if not isinstance(payload_list, list):
            logger.error("payload 应为列表形式")
            return

        for payload in payload_list:

            action = payload.action
            target_ip = payload.target_ip
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
