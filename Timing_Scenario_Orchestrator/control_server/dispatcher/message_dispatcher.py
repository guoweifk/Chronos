#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-29 20:50 
@file: message_dispatcher.py
@project: GW_My_tools
@describe: Powered By GW
"""
# !/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-28 22:56 
@file: message_dispatcher.py
@project: GW_My_tools
@describe: Powered By GW
"""
from Timing_Scenario_Orchestrator.control_server.dispatcher.agent_netem_command_processor import AgentNetemCommandProcessor
from Timing_Scenario_Orchestrator.control_server.dispatcher.agent_traffic_command_processor import AgentTrafficCommandProcessor
from Timing_Scenario_Orchestrator.control_server.dispatcher.server_traffic_command_processor import ServerTrafficCommandProcessor
from Timing_Scenario_Orchestrator.control_server.dispatcher.server_python_command_processor import ServerPythonCommandProcessor
from Timing_Scenario_Orchestrator.control_server.message.base_message import AgentNetemControlMessage, AgentTrafficControlMessage, \
    ServerTrafficControlMessage, ServerPythonCommandMessage
from Timing_Scenario_Orchestrator.control_server.utils.logutil import get_logger
from Timing_Scenario_Orchestrator.control_server.dispatcher.server_link_limit_command_processor import \
    ServerLinkLimitCommandProcessor
from Timing_Scenario_Orchestrator.control_server.message.base_message import ServerLinkLimitControlMessage

logger = get_logger("load_control_manager")


class ServerMessageDispatcher:
    def __init__(self):
        self.netem_processor = AgentNetemCommandProcessor()
        self.agent_traffic_processor = AgentTrafficCommandProcessor()
        self.server_traffic_processor = ServerTrafficCommandProcessor()
        self.server_python_cmd_processor = ServerPythonCommandProcessor()
        self.server_link_limit_processor = ServerLinkLimitCommandProcessor()

    def dispatch(self, msg):
        msg_type = msg.get("type")
        logger.info(f"msg:" + msg_type)

        if msg_type == "agent_netem":
            msg_obj = AgentNetemControlMessage.from_dict(msg)
            return self.netem_processor.handle(msg_obj)

        elif msg_type == "agent_traffic":
            msg_obj = AgentTrafficControlMessage.from_dict(msg)
            return self.agent_traffic_processor.handle(msg_obj)

        elif msg_type == "server_traffic":
            msg_obj = ServerTrafficControlMessage.from_dict(msg)
            return self.server_traffic_processor.handle(msg_obj)

        elif msg_type == "exec_python":
            msg_obj = ServerPythonCommandMessage.from_dict(msg)
            return self.server_python_cmd_processor.handle(msg_obj)
        elif msg_type == "server_link_limit":
            msg_obj = ServerLinkLimitControlMessage.from_dict(msg)
            return self.server_link_limit_processor.handle(msg_obj)

        else:
            logger.warning(f"[!] 未知消息类型: {msg_type}")
