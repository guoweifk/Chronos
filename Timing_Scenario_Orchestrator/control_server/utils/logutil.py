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

# 日志文件统一写入当前目录的 fixed 文件名
LOG_FILE_NAME = "control_server_manager.log"
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE_NAME)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

def get_logger(name="default", level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s %(filename)s:%(lineno)d - %(message)s"
    )

    # 控制台 handler（只添加一次）
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 文件 handler（只添加一次）
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(LOG_PATH)
               for h in logger.handlers):
        file_handler = logging.FileHandler(LOG_PATH)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
