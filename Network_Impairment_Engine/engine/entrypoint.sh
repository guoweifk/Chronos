#!/bin/bash

# 启动原始容器命令（Open5GS 主进程等）作为后台进程
exec "$@" &

# 切换到 engine 的上级目录（/opt）
cd /opt || exit 1

# 启动 Agent 控制器
python3 -m agent.load_control_agent &

# 阻止容器提前退出，等待所有后台任务
wait
