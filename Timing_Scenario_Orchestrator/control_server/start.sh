#!/bin/bash

# 后台启动，不阻塞终端
python3 -m control_server.load_control_manager &
echo "[+] 控制服务已启动，PID: $!"
