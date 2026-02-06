#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-11-14 17:52 
@file: test_graph.py
@project: GW_My_tools
@describe: Powered By GW
"""


# 1. 直接调用center函数，调用server的接口，获取当前docker 有哪些；还有状态。根据此状态目标server的初始状态图。
# 2. 开始注入扰动
# 3. 持续获取server的网元状态，识别到有掉线，就停止持续识别。
# 4. 根据当前关掉的docker，生成一个故障图。

def init():
    raw = send_python_cmd_to_server()
    items = [x.strip().upper() for x in raw.splitlines() if x.strip()]
    # 最小子图示例
    targets = ["UE", "AMF"]
    nodes_sub, edges_sub = minimal_subgraph(graph, targets)
    print("=== minimal_subgraph(SRS_UE, UPF) ===")
    print("子图节点:", nodes_sub)
    print("子图边:")
    for u, v in sorted(edges_sub):
        print(f"{u} -- {v}")
    #加一个写到文件中。
def watch_log():
    #一直监听网元状态，并且把地形输出。
    raw = send_python_cmd_to_server()
    items = [x.strip().upper() for x in raw.splitlines() if x.strip()]
    # 最小子图示例
def failure_graph():
    raw = send_python_cmd_to_server()
    items = [x.strip().upper() for x in raw.splitlines() if x.strip()]
    ##找到 bu running的网元。
    # 一跳子图示例（AMF）
    one_nodes, one_edges = one_hop_subgraph(graph, "AMF")
    print("\n=== one_hop_subgraph(AMF) ===")
    print("子图节点:", one_nodes)
    print("子图边:")
    for u, v in sorted(one_edges):
        print(f"{u} -- {v}")
    #保存图到另一个文件。

if __name__ == "__main__":

    # targets = ["UE", "AMF"]
    # nodes_sub, edges_sub = minimal_subgraph(graph, targets)
    # print("=== minimal_subgraph(SRS_UE, UPF) ===")
    # print("子图节点:", nodes_sub)
    # print("子图边:")
    # for u, v in sorted(edges_sub):
    #     print(f"{u} -- {v}")
    #
    # one_nodes, one_edges = one_hop_subgraph(graph, "AMF")
    # print("\n=== one_hop_subgraph(AMF) ===")
    # print("子图节点:", one_nodes)
    # print("子图边:")
    # for u, v in sorted(one_edges):
    #     print(f"{u} -- {v}")


    raw = send_python_cmd_to_server()
    items = [x.strip().upper() for x in raw.splitlines() if x.strip()]
    print(items)
