#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-28 22:29 
@file: logutil.py.py
@project: GW_My_tools
@describe: Powered By GW
"""

import os
import logging

# 自动定位 /mnt 下的唯一子目录作为日志目录
mnt_root = "/mnt"
mnt_subdirs = [d for d in os.listdir(mnt_root) if os.path.isdir(os.path.join(mnt_root, d))]
if not mnt_subdirs:
    raise RuntimeError("未找到 /mnt 下的有效子目录！")

mnt_target_dir = os.path.join(mnt_root, mnt_subdirs[0])
log_path = os.getenv("LOG_FILE", os.path.join(mnt_target_dir, "load_control_agent.log"))
os.makedirs(os.path.dirname(log_path), exist_ok=True)

def get_logger(name="default", level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 防止重复添加 handler
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s")

    # 控制台输出 handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出 handler
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

