#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 17:38 
@file: traffic_worker.py
@project: GW_My_tools
@describe: Powered By GW
"""
import socket
import time
from Network_Impairment_Engine.utils.logutil import get_logger

logger = get_logger("load_control_agent")


def traffic_worker(target_ip: str, target_port: int, rate: str, count: int, interval: float):
    logger.info(f"开始流量发送: target={target_ip}:{target_port}, rate={rate}, count={count}, interval={interval}s")
    target_port = int(target_port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


    packet_size = int(rate)  # 约等于 10Mbps/1秒 if 每秒发一个包

    # 构造固定大小的 payload 数据
    payload = b'X' * packet_size
    try:
        if count == 0:
            logger.info("[∞] 持续发送模式开启（count=0）")
            while True:
                sock.sendto(payload, (target_ip, target_port))
                time.sleep(0.001)
        else:
            for i in range(count):
                sock.sendto(payload, (target_ip, target_port))
                time.sleep(0.001)
    except Exception as e:
        logger.error(f"[×] 发送流量出错: {e}")
    finally:
        sock.close()
        logger.info("完成流量发送任务")

# ifstat -i eth0 1
