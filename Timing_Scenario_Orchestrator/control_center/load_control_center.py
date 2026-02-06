#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-28 16:06 
@file: load_control_center.py
@project: GW_My_tools
@describe: Powered By GW
"""
from dispatcher.server_control_processor import *

file_name = "free5gc_netem_profiles.json"
if __name__ == "__main__":
    # send_netem_config_to_agent(file_name)
    send_server_link_limit_config_to_server()
    # send_python_cmd_to_server()
    # send_traffic_config_to_server()
    # send_traffic_config_to_agent()
