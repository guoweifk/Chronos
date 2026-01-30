#!/usr/bin/env python
# -*- coding:utf-8 -*-

import subprocess
import os
from control_server.dispatcher.base_processor import BaseProcessor
from control_server.message.base_message import ServerLinkLimitControlMessage
from control_server.utils.container_ip_config import ContainerIPConfig
from control_server.utils.logutil import get_logger

logger = get_logger("load_control_manager")

IFACE = os.getenv("NET_IFACE", "enahisic2i0")
DEFAULT_BURST = "1000kbit"


def run_cmd(cmd: str):
    logger.info(f"[tc] {cmd}")
    subprocess.run(cmd, shell=True, check=False)


class ServerLinkLimitCommandProcessor(BaseProcessor):

    def handle(self, msg: ServerLinkLimitControlMessage):
        results = []
        # 默认配置即可
        container_ip_config = ContainerIPConfig()
        # 确保 clsact 存在（支持 ingress + egress）
        run_cmd(f"tc qdisc replace dev {IFACE} clsact")

        for p in msg.payload:
            container = p.container
            direction = p.direction
            ip = container_ip_config.get_ip(container)

            if not ip:
                results.append({
                    "container": container,
                    "status": "error",
                    "reason": "container ip not found"
                })
                continue

            pref = abs(hash(f"{container}-{direction}")) % 40000 + 1000

            # ========= 1. 带宽限制（police） =========
            if p.rate:
                burst = p.burst or DEFAULT_BURST

                if direction == "uplink":
                    run_cmd(f"tc filter del dev {IFACE} ingress pref {pref} 2>/dev/null")
                    run_cmd(
                        f"tc filter add dev {IFACE} ingress pref {pref} "
                        f"protocol ip u32 match ip dst {ip} "
                        f"police rate {p.rate} burst {burst} drop"
                    )

                elif direction == "downlink":
                    run_cmd(f"tc filter del dev {IFACE} egress pref {pref} 2>/dev/null")
                    run_cmd(
                        f"tc filter add dev {IFACE} egress pref {pref} "
                        f"protocol ip u32 match ip src {ip} "
                        f"police rate {p.rate} burst {burst} drop"
                    )

            # ========= 2. netem 劣化（delay / loss / reorder / duplicate） =========
            netem_args = []

            if p.delay:
                if p.jitter:
                    netem_args.append(f"delay {p.delay} {p.jitter}")
                else:
                    netem_args.append(f"delay {p.delay}")

            if p.loss:
                netem_args.append(f"loss {p.loss}")

            if p.duplicate:
                netem_args.append(f"duplicate {p.duplicate}")

            if p.reorder:
                if p.reorder_corr:
                    netem_args.append(f"reorder {p.reorder} {p.reorder_corr}")
                else:
                    netem_args.append(f"reorder {p.reorder}")

            if netem_args:
                netem_cmd = " ".join(netem_args)

                # 覆盖式：直接 replace
                run_cmd(
                    f"tc qdisc replace dev {IFACE} root netem {netem_cmd}"
                )

            results.append({
                "container": container,
                "ip": ip,
                "direction": direction,
                "rate": p.rate,
                "delay": p.delay,
                "jitter": p.jitter,
                "loss": p.loss,
                "duplicate": p.duplicate,
                "reorder": p.reorder,
                "status": "applied"
            })

        return results
