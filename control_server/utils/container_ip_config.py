#!/usr/bin/env python
# -*- coding:utf-8 -*-

import json
import os
from control_server.utils.logutil import get_logger

logger = get_logger("load_control_manager")

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "container_ip_config.json"
)


class ContainerIPConfig:
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = config_path
        self.mapping = {}
        self.load()

    def load(self):
        try:
            with open(self.config_path, "r") as f:
                self.mapping = json.load(f)
            logger.info(f"[✓] 加载 container IP 配置成功: {self.config_path}")
        except Exception as e:
            logger.error(f"[×] 加载 container IP 配置失败: {e}")
            self.mapping = {}

    def get_ip(self, container: str):
        return self.mapping.get(container)
