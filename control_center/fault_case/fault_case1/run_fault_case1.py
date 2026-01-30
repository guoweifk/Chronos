#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-11-14 17:52
@file: run_fault_case2.py
@project: GW_My_tools
@describe: Powered By GW

功能说明（长监听版本 + 扰动控制）：
- 持续监听目标网络网元状态：
  1）判断是否出现 EXITED / DOWN（故障）
  2）解析当前所有网元状态，构造 minimal_subgraph 图
  3）生成故障关键地形（以失败节点为中心的一跳子图），写入存储目录
- 启动 Web 接口监听扰动控制：
  1）/attack/start：触发一次 HTTP 扰动注入
  2）/attack/status：查询当前扰动状态
- 监控循环中根据扰动是否已触发，持续打印不同的描述
"""

from control_center.dispatcher.agent_control_processor import *
from control_center.dispatcher.server_control_processor import *
from control_center.autoAnalysis.get_min_graph import *  # 假定其中提供 minimal_subgraph / one_hop_subgraph
from control_center.fault_case.fault_case1.land_graph import *  # 提供全局拓扑 graph

import time
import os
import json
import logging
import sys
import threading
import requests
from flask import Flask, jsonify, request

# ====== 记录仅打印一次路径 ======
_printed_cmd_path = set()

logger = logging.getLogger(__name__)

# ====== 阶段标记：控制那几句只执行一次 ======
INITIAL_PHASE_REPORTED = False
ATTACK_PHASE_REPORTED = False
FAILURE_PHASE_REPORTED = False


# ======================================================
# DualLogger —— print → 控制台 + 文件
# ======================================================
class DualLogger:
    def __init__(self, filename_prefix="full_run_log"):
        ts = time.strftime("%Y%m%d_%H%M%S")
        self.filename = f"{filename_prefix}_{ts}.txt"
        self.log_file = open(self.filename, "a", encoding="utf-8")
        self.console = sys.stdout

    def write(self, msg):
        self.console.write(msg)
        self.log_file.write(msg)

    def flush(self):
        self.console.flush()
        self.log_file.flush()


# ======================================================
# FullProcessRecorder —— 全过程记录表（单独文本文件）
# ======================================================
class FullProcessRecorder:
    def __init__(self, storage_dir: str = "storage", filename_prefix: str = "full_process_record"):
        os.makedirs(storage_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(storage_dir, f"{filename_prefix}_{ts}.txt")

    def log(self, message: str):
        """
        写入一行：[YYYY-MM-DD HH:MM:SS] 消息
        消息内容完全使用用户给定文本，不做改写。
        """
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")


# ======================================================
# 发送 python cmd
# ======================================================
def send_python_cmd_to_server(status_only=False, python_cmd_path=None):
    global _printed_cmd_path

    if python_cmd_path is None:
        raise ValueError("python_cmd_path 必须传入！")

    python_cmd_path = os.path.abspath(python_cmd_path)

    try:
        with open(python_cmd_path, "r", encoding="utf-8") as f:
            full_profile = json.load(f)

        if python_cmd_path not in _printed_cmd_path:
            logger.info(f"[状态监控] 使用配置: {python_cmd_path}，目标宿主机: {len(full_profile)}")
            _printed_cmd_path.add(python_cmd_path)

    except Exception as e:
        logger.error(f"[状态监控] 配置文件加载失败: {e}")
        return ""

    all_outputs = []

    for host_ip, profiles in full_profile.items():

        if not profiles or not isinstance(profiles, list):
            logger.error(f"[状态监控] {host_ip} 配置格式错误：{profiles}")
            continue

        # status_only=True 时，只取第一个配置做查询
        payload = [profiles[0]] if status_only else profiles

        msg = ServerPythonCommandMessage(
            type="exec_python",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            target_server_ip=host_ip,
            payload=payload,
        )

        ok, resp = send_to_server(host_ip, msg)
        time.sleep(0.3)

        if not ok or not resp:
            logger.error(f"[状态监控] 查询失败 {host_ip}")
            continue

        all_outputs.append(resp[0].get("stdout", ""))

    return "\n".join(all_outputs)


# ======================================================
# 工具函数：解析网元状态
# ======================================================
def parse_items(raw: str):
    """
    将 stdout 解析为：
    - items: 原始大写行列表（用于打印）
    - failed_nodes: EXITED/DOWN 的网元名（清洗过）
    - alive_nodes: 正常网元名（清洗过）
    解析规则：
      - 每行按空格 split
      - 若最后一个 token 是状态（EXITED/DOWN/RUNNING/UP），前面的部分视为网元名
    """

    # 原始行，保留大小写用于打印
    raw_lines = [x.strip() for x in raw.splitlines() if x.strip()]

    STATUS_FAIL = {"EXITED", "DOWN"}
    STATUS_OK = {"RUNNING", "UP"}

    items_upper = []      # 给外面打印用（全大写）
    failed_nodes = []     # 失败网元名（清洗后）
    alive_nodes = []      # 正常网元名（清洗后）

    def parse_line(line: str):
        """
        返回 (name, status)
        - name: 网元名（大写）
        - status: EXITED / DOWN / RUNNING / UP / None
        """
        upper = line.upper()
        tokens = upper.split()
        if not tokens:
            return "", None

        status = None
        name_tokens = tokens

        # 若最后一个 token 是状态，则前面的是网元名
        if tokens[-1] in STATUS_FAIL | STATUS_OK:
            status = tokens[-1]
            name_tokens = tokens[:-1]

        name = " ".join(name_tokens).strip()
        return name, status

    # 去重保持顺序的小工具
    def _unique(seq):
        seen = set()
        out = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    for line in raw_lines:
        name, status = parse_line(line)
        if not name:
            continue

        items_upper.append(line.upper())

        if status in STATUS_FAIL:
            failed_nodes.append(name)
        else:
            alive_nodes.append(name)

    return items_upper, _unique(failed_nodes), _unique(alive_nodes)


# ======================================================
# 工具函数：保存图到文件
# ======================================================
def save_graph(nodes, edges, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("NODES:\n")
        for n in nodes:
            f.write(f"{n}\n")

        f.write("\nEDGES:\n")
        for u, v in edges:
            f.write(f"{u} -- {v}\n")


# ======================================================
# 构造 minimal_subgraph 图（基于当前在线网元）
# ======================================================
def build_minimal_graph(alive_nodes):
    """
    将当前所有网元（或在线网元）转换为 minimal_subgraph。
    这里假定 get_min_graph.py 中提供 minimal_subgraph(graph, nodes) 接口。
    若不存在，则退化为简单“子图”构造。
    """
    if not alive_nodes:
        return [], []

    try:
        # 推荐接口（若存在）
        nodes_sub, edges_sub = minimal_subgraph(graph, alive_nodes)  # type: ignore
    except NameError:
        # 兜底实现：只保留 alive_nodes 之间在 graph 中存在的边
        nodes_sub = [n for n in alive_nodes if n in graph]
        edges_set = set()
        for u in nodes_sub:
            for v in graph.get(u, []):
                if v in nodes_sub:
                    edges_set.add(tuple(sorted((u, v))))
        edges_sub = sorted(edges_set)

    return nodes_sub, edges_sub


# ======================================================
# 故障关键地形图（以失败节点为中心的一跳子图）
# ======================================================
def build_failure_graph(failed_nodes):
    print("\n[故障状态] 生成失败节点关键地形...\n")

    combined_nodes = set()
    combined_edges = set()

    for fn in failed_nodes:
        if fn not in graph:
            print(f"[警告] 失败节点 {fn} 不在拓扑中，跳过。")
            continue

        # one_hop_subgraph 由 get_min_graph 提供
        one_nodes, one_edges = one_hop_subgraph(graph, fn)

        print("\n=== 故障节点关键地形 ===")
        print("节点:", one_nodes)
        print("边:")
        for u, v in sorted(one_edges):
            print(f"{u} -- {v}")

        combined_nodes.update(one_nodes)
        combined_edges.update(one_edges)

    return sorted(combined_nodes), sorted(combined_edges)


# ======================================================
# 扰动注入（攻击逻辑）
# ======================================================
def inject_fault_once(api_url="http://192.168.80.200:8080/zh/start"):
    """
    调用外部 HTTP 接口触发一次扰动注入。
    """
    ts_start = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[扰动开始] {ts_start} 开始执行 HTTP 扰动注入...")

    try:
        resp = requests.get(api_url, timeout=5)
        print("[扰动开始] HTTP 返回:", resp.status_code)
        print("[扰动开始] 内容:", resp.text)
    except Exception as e:
        print("[扰动开始] HTTP 请求失败:", e)
        return False

    ts_end = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[扰动开始] {ts_end} 非法参数值扰动注入完成。\n")

    return True


# ======================================================
# 扰动状态（供监控 loop 打印描述用）
# ======================================================
ATTACK_STATE = {
    "started": False,          # 是否已经触发过扰动
    "last_start_time": None,   # 最近一次触发时间
    "last_result": None,       # "success" / "failed"
}
STATE_LOCK = threading.Lock()


def set_attack_state(started: bool, result: str | None):
    with STATE_LOCK:
        ATTACK_STATE["started"] = started
        ATTACK_STATE["last_start_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        ATTACK_STATE["last_result"] = result


def get_attack_state():
    with STATE_LOCK:
        return dict(ATTACK_STATE)


# ======================================================
# 读取扰动配置（netem / parameter_set）—— 可选保留
# ======================================================
def load_netem_config(netem_config_path: str | None):
    if not netem_config_path:
        return {}

    try:
        with open(netem_config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[扰动配置] 无法加载 {netem_config_path}: {e}")
        return {}


# ======================================================
# 长监听主循环（监控 + 打印 + 图生成）
# ======================================================
def long_monitor_loop(
    python_cmd_path: str,
    netem_config_path: str | None = None,
    storage_dir: str = "storage",
    recorder: FullProcessRecorder | None = None,
):
    """
    长驻监听：
    1. 持续调用 send_python_cmd_to_server(status_only=True) 监测网元状态；
    2. 没有 EXITED/DOWN 时，认为系统正常，并基于所有网元生成 minimal_subgraph；
    3. 检测到故障时，生成故障关键地形，并写入存储目录；
    4. 同时将关键描述写入“初始状态到故障状态的全过程记录表”。
    """
    global INITIAL_PHASE_REPORTED, ATTACK_PHASE_REPORTED, FAILURE_PHASE_REPORTED

    print("\n===== 长监听任务启动 =====\n")
    print(f"[监听配置] python_cmd_path = {python_cmd_path}")
    if netem_config_path:
        print(f"[监听配置] netem_config_path = {netem_config_path}")
    print(f"[监听配置] storage_dir = {storage_dir}\n")

    # 初次加载扰动配置（可选）
    netem_config = load_netem_config(netem_config_path)
    if netem_config:
        print("[扰动配置] 已检测到扰动参数文件（parameter_set）：")
    else:
        print("[扰动配置] 当前未检测到有效扰动参数文件。")

    os.makedirs(storage_dir, exist_ok=True)

    last_print_time = 0
    last_failure_nodes = set()
    last_min_nodes = None
    last_min_edges = None

    while True:
        # 1. 拉取当前网元状态
        raw = send_python_cmd_to_server(
            status_only=True,
            python_cmd_path=python_cmd_path
        )
        items, failed_nodes, alive_nodes = parse_items(raw)

        # 当前扰动状态
        state = get_attack_state()

        # ===== 初始阶段：无故障 + 未注入扰动 =====
        if (not INITIAL_PHASE_REPORTED) and (not failed_nodes) and (not state["started"]):
            # 控制台打印一句
            print("系统处于初始状态，当前无故障，并未注入扰动。")
            # 全过程记录表写三句（带时间戳）
            if recorder:
                recorder.log("系统处于初始状态，当前无故障，并未注入扰动。")
                recorder.log("系统创建新的初始状态到故障状态的全过程记录表。")
                recorder.log("系统将初始关键地形写入全过程记录表。")
            INITIAL_PHASE_REPORTED = True

        # ===== 扰动注入阶段：已经通过 /attack/start 触发，但尚未检测到故障 =====
        if state["started"] and (not failed_nodes) and (not ATTACK_PHASE_REPORTED):
            # 控制台打印一句
            print("系统开始注入关系内禀随机性对应的扰动，正在持续监听目标网络状态。")
            # 全过程记录表写三句
            if recorder:
                recorder.log("系统开始注入关系内禀随机性对应的扰动，正在持续监听目标网络状态。")
                recorder.log("系统持续将“系统开始注入关系内禀随机性对应的扰动，正在持续监听目标网络状态”写入全过程记录表。")
                recorder.log("系统持续将关系内禀随机性对应的关键地形写入全过程记录表。")
            ATTACK_PHASE_REPORTED = True

        # 2. 判断故障
        if failed_nodes:
            # 只有当故障节点集合发生变化时，才打印+落盘
            if set(failed_nodes) != last_failure_nodes:
                print("\n[故障状态] 检测到异常网元:", failed_nodes)

                fail_nodes, fail_edges = build_failure_graph(failed_nodes)

                ts = time.strftime("%Y%m%d_%H%M%S")
                failure_graph_path = os.path.join(
                    storage_dir, f"failure_subgraph_{ts}.txt"
                )
                save_graph(fail_nodes, fail_edges, failure_graph_path)
                print(f"[故障状态] 故障关键地形已写入: {failure_graph_path}\n")

                # ===== 故障阶段：已注入扰动 + 目标网络发生故障 =====
                # 故障网元字符串，故障哪个写哪个
                failed_str = "、".join(failed_nodes) if failed_nodes else "目标网元"

                # 控制台打印两句（其中第二句带具体网元名）
                print("已注入扰动，目标网络发生故障。")
                print(f"关系内禀随机性对应的扰动生效，目标网络{failed_str}网元程序崩溃。")

                # 全过程记录表写四句
                if recorder:
                    recorder.log("已注入扰动，目标网络发生故障。")
                    recorder.log("系统将“已注入扰动，目标网络发生故障”和故障关键地形写入全过程记录表。")
                    recorder.log(f"关系内禀随机性对应的扰动生效，目标网络{failed_str}网元程序崩溃。")
                    recorder.log(f"系统将“关系内禀随机性对应的扰动生效，目标网络{failed_str}网元程序崩溃”写入全过程记录表。")

                FAILURE_PHASE_REPORTED = True

                # ========= 首次故障后结束监听 =========
                print("[全过程结束] 已捕获故障节点及关键地形，监听任务结束。\n")
                return

        else:
            # 没有 EXITED / DOWN，认为系统整体健康
            if last_failure_nodes:
                print("[故障状态] 之前存在故障节点，目前已无 EXITED/DOWN，视作已恢复。\n")
                last_failure_nodes = set()

        # 3. 不管是否故障，都基于当前网元构造 minimal_subgraph
        #    这里使用 alive_nodes（即没有 EXITED/DOWN 的网元）
        min_nodes, min_edges = build_minimal_graph(alive_nodes)

        # 若 minimal_subgraph 发生变化，则写入一个“最新快照”
        if (min_nodes, min_edges) != (last_min_nodes, last_min_edges):
            latest_min_path = os.path.join(storage_dir, "minimal_subgraph_latest.txt")
            save_graph(min_nodes, min_edges, latest_min_path)
            last_min_nodes, last_min_edges = min_nodes, min_edges
            print(f"[关键地形] 当前 minimal_subgraph 已更新并写入: {latest_min_path}")

        # 4. 每 10 秒输出一次整体状态 + 扰动信息
        now = time.time()
        if now - last_print_time >= 10:
            print("\n[周期状态] 当前网元原始状态行（每10秒输出一次）:")
            for it in items:
                print(" -", it)

            if failed_nodes:
                print(f"[周期状态] 当前存在故障网元: {failed_nodes}")
            else:
                print("[周期状态] 当前未检测到 EXITED/DOWN，系统整体处于健康状态。")

            # 扰动参数文件（静态）
            if netem_config_path:
                netem_config = load_netem_config(netem_config_path)

            # 当前扰动状态（是否已经通过 /attack/start 触发）
            state = get_attack_state()
            if not state["started"]:
                print(f"[扰动过程监控] 当前尚未通过 /attack/start 注入扰动，"
                      f"等待触发指令... (最近结果: {state['last_result']}, 时间: {state['last_start_time']})")
            else:
                print(f"[扰动过程监控] 扰动已注入（时间: {state['last_start_time']}，结果: {state['last_result']}），"
                      f"请结合故障态输出与关键地形进行分析。")

            print()  # 空行
            last_print_time = now

        time.sleep(1)


# ======================================================
# Flask Web 接口（攻击控制）
# ======================================================
app = Flask(__name__)


@app.route("/attack/start", methods=["GET", "POST"])
def http_attack_start():
    """
    调用方式：
      - GET  /attack/start
      - POST /attack/start

    逻辑：
      - 若已经触发过扰动，则直接返回当前状态（不重复攻击）
      - 否则调用 inject_fault_once() 执行一次扰动
      - 更新 ATTACK_STATE
    """
    state_before = get_attack_state()
    if state_before["started"]:
        return jsonify({
            "code": 0,
            "msg": "扰动已触发，无需重复执行",
            "data": state_before
        }), 200

    ok = inject_fault_once()
    if ok:
        set_attack_state(True, "success")
        state_after = get_attack_state()
        return jsonify({
            "code": 0,
            "msg": "扰动触发成功",
            "data": state_after
        }), 200
    else:
        set_attack_state(False, "failed")
        state_after = get_attack_state()
        return jsonify({
            "code": 1,
            "msg": "扰动触发失败",
            "data": state_after
        }), 500


@app.route("/attack/status", methods=["GET"])
def http_attack_status():
    """
    查询当前扰动状态：
      - 是否已经开始
      - 最近一次触发时间
      - 最近一次结果
    """
    return jsonify({
        "code": 0,
        "msg": "ok",
        "data": get_attack_state()
    }), 200


# ======================================================
# 主入口
# ======================================================
if __name__ == "__main__":

    # 所有 print 同时写入控制台 + 日志文件
    sys.stdout = DualLogger("full_run_log")

    print("===== 开始记录完整流程日志（长监听 + 扰动控制模式） =====\n")

    # 根据实际情况修改这三个参数
    PYTHON_CMD_PATH = "python_cmd.json"
    NETEM_CONFIG_PATH = "parameter_set_case1.json"   # 如不需要监听参数文件，可改为 None
    STORAGE_DIR = "storage"                          # 关键地形与 minimal_subgraph 的落盘目录

    # 创建“初始状态到故障状态的全过程记录表”记录器
    recorder = FullProcessRecorder(storage_dir=STORAGE_DIR)

    # 启动监控线程（daemon）
    t_monitor = threading.Thread(
        target=long_monitor_loop,
        kwargs={
            "python_cmd_path": PYTHON_CMD_PATH,
            "netem_config_path": NETEM_CONFIG_PATH,
            "storage_dir": STORAGE_DIR,
            "recorder": recorder,
        },
        daemon=True
    )
    t_monitor.start()

    # 启动 Web 服务（监听攻击指令）
    print("===== 扰动控制 Web 服务启动 =====")
    print("说明：")
    print("  - 调用 /attack/start 触发一次 HTTP 扰动注入；")
    print("  - 调用 /attack/status 查看当前扰动状态；")
    print("  - 监控线程会根据扰动状态，持续打印不同的过程描述。\n")

    app.run(host="0.0.0.0", port=8989, debug=False)
