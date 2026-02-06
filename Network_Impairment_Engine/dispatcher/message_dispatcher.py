#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-28 22:56 
@file: message_dispatcher.py
@project: GW_My_tools
@describe: Powered By GW
"""
from Network_Impairment_Engine.dispatcher.netem_processor import NetemProcessor
from Network_Impairment_Engine.dispatcher.traffic_generator_processor import TrafficGeneratorProcessor
from Network_Impairment_Engine.message.base_message import AgentNetemMessage,AgentTrafficMessage
from Network_Impairment_Engine.utils.logutil import get_logger

logger = get_logger("load_control_agent")


class AgentMessageDispatcher:
    def __init__(self):
        self.netem_processor = NetemProcessor()
        self.traffic_processor = TrafficGeneratorProcessor()

    def dispatch(self, msg):
        msgType = msg.get("type")
        if msgType == "agent_netem":
            msg = AgentNetemMessage.from_dict(msg)
            self.netem_processor.handle(msg)
        elif msgType == "agent_traffic":
            msg = AgentTrafficMessage.from_dict(msg)
            self.traffic_processor.handle(msg)
        else:
            logger.error("unknown message type: %s", msgType)

