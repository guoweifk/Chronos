#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-06-28 22:23 
@file: base_processor.py
@project: GW_My_tools
@describe: Powered By GW
"""
class BaseProcessor:
    def handle(self, payload: dict):
        raise NotImplementedError
