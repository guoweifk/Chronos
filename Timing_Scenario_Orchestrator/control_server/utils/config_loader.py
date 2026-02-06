#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 21:09 
@file: config_loader.py
@project: GW_My_tools
@describe: Powered By GW
"""
# config_loader.py
import json
import os
from Timing_Scenario_Orchestrator.control_server.utils.logutil import get_logger

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "agent_ip_config.json")

logger = get_logger("load_control_manager")

class AgentIPConfig:
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = config_path
        self.agent_ip_mapping = {}
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.agent_ip_mapping = json.load(f)
                logger.info(f"[✓] 成功加载配置: {self.config_path}")
        except Exception as e:
            logger.error(f"[×] 加载配置失败: {e}")
            self.agent_ip_mapping = {}

    def get_ip(self, service_name):
        return self.agent_ip_mapping.get(service_name)

    def all_services(self):
        return self.agent_ip_mapping.keys()

    def all_mappings(self):
        return self.agent_ip_mapping.copy()
