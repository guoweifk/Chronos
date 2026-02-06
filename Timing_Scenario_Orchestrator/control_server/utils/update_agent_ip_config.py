#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动获取所有 Docker 容器的 (container_name -> IP) 映射，
并覆盖写入 agent_ip_config.json
"""

import subprocess
import json
import os
import sys


# ======== 你可以根据项目结构微调这里 ========
AGENT_IP_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "control_server/utils/agent_ip_config.json"
)
# ===========================================


def run_cmd(cmd: list) -> str:
    """运行 shell 命令并返回 stdout"""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def get_all_containers():
    """
    返回所有运行中的容器名列表
    """
    output = run_cmd(["docker", "ps", "--format", "{{.Names}}"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_container_ip(container_name: str) -> str | None:
    """
    获取单个容器的 IP（取第一个 network 的 IP）
    """
    output = run_cmd([
        "docker", "inspect", container_name,
        "--format",
        "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"
    ])
    return output if output else None


def build_container_ip_map():
    """
    构建 {container_name: ip} 映射
    """
    mapping = {}
    containers = get_all_containers()

    for name in containers:
        try:
            ip = get_container_ip(name)
            if ip:
                mapping[name] = ip
            else:
                print(f"[WARN] 容器 {name} 未获取到 IP，跳过")
        except Exception as e:
            print(f"[ERROR] 获取 {name} IP 失败: {e}")

    return mapping


def write_agent_ip_config(mapping: dict):
    """
    覆盖写入 agent_ip_config.json
    """
    os.makedirs(os.path.dirname(AGENT_IP_CONFIG_PATH), exist_ok=True)

    with open(AGENT_IP_CONFIG_PATH, "w") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print(f"[✓] 已更新 {AGENT_IP_CONFIG_PATH}")
    print(json.dumps(mapping, indent=2, ensure_ascii=False))


def update_and_write_ip():
    mapping = build_container_ip_map()
    if not mapping:
        print("[×] 未获取到任何容器 IP，文件未更新")
        sys.exit(1)

    write_agent_ip_config(mapping)


if __name__ == "__main__":
    update_and_write_ip()
