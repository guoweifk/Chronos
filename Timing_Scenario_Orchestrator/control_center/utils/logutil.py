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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 当前模块所在目录
DEFAULT_LOG_DIR = os.path.join(BASE_DIR, "log")
os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)  # 自动创建目录（如果不存在）

def get_logger(name="default", level=logging.INFO):
    # 从环境变量读取路径或使用默认路径
    log_path = os.getenv("LOG_FILE", os.path.join(DEFAULT_LOG_DIR, "control_server.log"))

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        return logger  # 防止重复添加

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
