import time
import os
import json
import logging
import sys

# ====== 全局禁止重复打印配置文件路径 ======
_printed_cmd_path = set()

logger = logging.getLogger(__name__)


# ======================================================
# DualLogger —— 将所有 print 写入文件 + 控制台
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
# 发送 python cmd（支持传入路径）
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
# 发送 netem 配置（支持传入路径）
# ======================================================
def send_netem_config_to_agent(config_path):
    config_path = os.path.abspath(config_path)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            full_profile = json.load(f)
            logger.info(f"[扰动] 已加载配置 {config_path}，宿主机数: {len(full_profile)}")
    except Exception as e:
        logger.error(f"配置文件加载失败: {e}")
        raise e

    for host_ip, profiles in full_profile.items():
        msg = AgentNetemControlMessage(
            type="agent_netem",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            target_server_ip=host_ip,
            payload=profiles,
        )
        send_to_server(host_ip, msg)
        time.sleep(1)


# ======================================================
# 1. 初始状态图（完整拓扑） —— 不再生成 txt，只写 full_run_log
# ======================================================
def get_initial_state(python_cmd_path):
    raw = send_python_cmd_to_server(
        status_only=False,
        python_cmd_path=python_cmd_path
    )

    items = [x.strip().upper() for x in raw.splitlines() if x.strip()]

    nodes_sub = list(graph.keys())

    edges_sub = set()
    print("=== 加载关系内禀随机性和电信网络空间三维立体图 ===")
    for u, neighbors in graph.items():
        if neighbors:
            for v in neighbors:
                edges_sub.add(tuple(sorted((u, v))))

    edges_sub = sorted(edges_sub)

    print("=== 初始完整地形 ===")
    print("节点:", nodes_sub)
    print("边:")
    for u, v in edges_sub:
        print(f"{u} -- {v}")

    print("\n[全过程记录表已生成] 初始拓扑已记录到 full_run_log\n")
    print("\n[故障状态] 初始状态无故障\n")
    print("\n[扰动开始] 尚未注入扰动\n")

    return items, (nodes_sub, edges_sub)


# ======================================================
# 2. 注入扰动（加入时间戳）
# ======================================================
def inject_fault_once(config_path):
    ts_start = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[扰动开始] {ts_start} 开始执行扰动注入（仅一次）...")

    send_netem_config_to_agent(config_path)

    ts_end = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[扰动开始] {ts_end} 生命周期管理缺陷类扰动注入完成。\n")


# ======================================================
# 3. 监控 & 每 10 秒打印一次在线状态
# ======================================================
# def wait_for_failure(python_cmd_path):
#     print("\n[扰动过程监控] 正在监听网元状态变化...\n")
#
#     last_print_time = time.time()
#
#     while True:
#         raw = send_python_cmd_to_server(
#             status_only=True,
#             python_cmd_path=python_cmd_path
#         )
#         items = [x.strip().upper() for x in raw.splitlines() if x.strip()]
#
#         failed = [x for x in items if "EXITED" in x or "DOWN" in x]
#
#         if failed:
#             print("\n[故障状态] 发现异常网元:", failed)
#
#             failed_clean = []
#             for f in failed:
#                 failed_clean.append(f.replace("EXITED", "").replace("DOWN", "").strip())
#
#             print("[处理后故障节点]:", failed_clean)
#             return failed_clean
#
#         now = time.time()
#         if now - last_print_time >= 10:
#             print("\n[扰动过程监控] 当前在线网元状态（每10秒输出一次）:")
#             for it in items:
#                 print(" -", it)
#             last_print_time = now
#
#         time.sleep(1)
def wait_for_failure(python_cmd_path):
    print("\n[扰动过程监控] 正在监听网元状态变化...\n")

    last_print_time = time.time()

    # ==================== 新增：读取已注入的 netem 配置 ====================
    netem_config = {}
    try:
        with open("parameter_set_case4.json", "r", encoding="utf-8") as f:
            netem_config = json.load(f)
    except:
        pass
    # =======================================================================

    while True:
        raw = send_python_cmd_to_server(
            status_only=True,
            python_cmd_path=python_cmd_path
        )
        items = [x.strip().upper() for x in raw.splitlines() if x.strip()]

        failed = [x for x in items if "EXITED" in x or "DOWN" in x]

        # =====================================================
        # 发现故障 → 输出并写文件
        # =====================================================
        if failed:
            print("\n[故障状态] 发现异常网元:", failed)

            ts = time.strftime("%Y%m%d_%H%M%S")
            filename = f"fault_event_{ts}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                for full in failed:
                    name = full.replace("EXITED", "").replace("DOWN", "").strip()
                    status = "EXITED" if "EXITED" in full else "DOWN"
                    f.write(f"网元 {name} 发生故障（{status}）\n")
                    f.write(f"详情请查看目标宿主机 {name} 的实时日志与程序日志。\n\n")

                f.write(f"发生时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")

            print(f"[故障状态] 已记录故障状态到文件: {filename}\n")

            failed_clean = [
                f0.replace("EXITED", "").replace("DOWN", "").strip()
                for f0 in failed
            ]

            print("[处理后故障节点]:", failed_clean)
            return failed_clean

        # =====================================================
        # 每 10 秒打印一次在线状态 + 全网地形 + 当前已注入配置
        # =====================================================
        now = time.time()
        if now - last_print_time >= 10:
            print("\n[扰动过程监控] 当前在线网元状态（每10秒输出一次）:")
            for it in items:
                print(" -", it)

            print("[扰动过程监控] 当前暂无故障，一切运行正常。\n")

            # ========= 当前实时地形输出 =========
            print("[扰动过程监控] 当前实时地形:")
            printed_edges = set()
            for u, nbrs in graph.items():
                for v in nbrs:
                    edge = tuple(sorted((u, v)))
                    if edge not in printed_edges:
                        printed_edges.add(edge)
                        print(f"   {edge[0]} -- {edge[1]}")


            # ========= 新增：输出已注入的扰动配置 =========
            print("[扰动过程监控] 当前已注入扰动配置")
            last_print_time = now

        time.sleep(1)




# ======================================================
# 4. 构建故障图 —— txt 删除，只写 full_run_log
# ======================================================
def build_failure_graph(failed_nodes):
    print("\n[故障状态] 生成失败节点拓扑...\n")

    combined_nodes = set()
    combined_edges = set()

    for fn in failed_nodes:
        if fn not in graph:
            print(f"[警告] 失败节点 {fn} 不在拓扑图中，跳过。")
            continue

        one_nodes, one_edges = one_hop_subgraph(graph, fn)

        print("\n=== 故障节点关键地形 ===")
        print("节点:", set(one_nodes))
        print("边:")
        for u, v in sorted(one_edges):
            print(f"{u} -- {v}")

        combined_nodes.update(one_nodes)
        combined_edges.update(one_edges)

    combined_nodes = sorted(combined_nodes)
    combined_edges = sorted(combined_edges)

    print("\n[全过程记录表已生成] 故障关键地形已记录到 full_run_log\n")

    return combined_nodes, combined_edges


# ======================================================
# 总流程
# ======================================================
def run_full_test(netem_config_path, python_cmd_path):
    print("\n===== 实验用例流程启动 =====\n")

    initial_state_raw, initial_graph = get_initial_state(python_cmd_path)

    inject_fault_once(netem_config_path)

    failed_nodes = wait_for_failure(python_cmd_path)

    fail_graph = build_failure_graph(failed_nodes)

    print("\n===== 测试结束 =====\n")
    return {
        "initial": initial_graph,
        "failed_nodes": failed_nodes,
        "failure_graph": fail_graph,
    }


# ======================================================
# 主入口
# ======================================================
if __name__ == "__main__":
    sys.stdout = DualLogger("full_run_log")

    print("===== 开始记录完整流程日志 =====\n")

    result = run_full_test(
        netem_config_path="parameter_set_case4.json",
        python_cmd_path="python_cmd.json"
    )

    print(result)
