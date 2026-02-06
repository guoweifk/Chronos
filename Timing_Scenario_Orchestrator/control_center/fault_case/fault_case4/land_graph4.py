# 所有网元的调用关系图（有边表示两者之间有直接协议/接口交互）
graph = {
    # ===== 基础设施 / 存储 / 监控 =====
    "MONGO": set(),             # Open5GS 配置存储，这里不参与信令路径
    "MYSQL": {"PYHSS"},         # PYHSS 使用 MySQL
    "METRICS": set(),           # Prometheus 等监控，这里不参与业务信令
    "WEBUI": {"MONGO"},         # WebUI 通过 MongoDB 管理配置
    "DNS": {"HSS", "MME", "AMF", "SMF", "UPF", "PCF", "NRF", "UDM"},

    # ===== 5GC 控制 / 用户面 =====
    "SMF": {"AMF", "UPF", "NRF", "UDM", "PCF", "BSF"},  # N11/N4/N7/N10
    "UPF": {"SMF", "SGWU"},                            # N4 / S1-U

    "AMF": {
        "NRF", "SMF", "AUSF", "UDM", "PCF", "NSSF",
        "SRS_GNB", "NR_GNB", "UE"
    },                                                 # N1/N2/N11/N12/N8/N15/N22

    "AUSF": {"AMF", "UDM", "NRF"},                     # N12/N13
    "NRF": {"AMF", "SMF", "AUSF", "UDM", "UDR", "PCF", "NSSF", "BSF", "SCP"},
    "UDM": {"AUSF", "NRF", "UDR", "AMF", "SMF"},       # Nudm
    "UDR": {"UDM", "NRF", "PCF"},                      # Nudr

    "PCF": {"AMF", "SMF", "NRF", "UDR", "NSSF", "BSF"},  # N7/N15 等
    "NSSF": {"AMF", "PCF", "NRF"},                      # N22
    "BSF": {"PCF", "SMF", "NRF", "ENTITLEMENT_SERVER"}, # 认证/策略绑定
    "SCP": {"NRF", "AMF", "SMF", "AUSF", "PCF", "UDM", "NSSF", "BSF"},  # SBA 代理

    # ===== RAN / UE 接入侧 =====
    "SRS_ENB": {"MME", "UE"},            # LTE eNB
    "NR_GNB": {"AMF", "UE"},            # 5G gNB
    "OAI_ENB": {"MME"},                     # OAI eNB
    "SRS_GNB": {"AMF", "UE"},           # srsRAN gNB
    "UE": {"SRS_ENB", "NR_GNB", "SRS_GNB", "AMF"},

}

# 标记“基础设施类节点”，默认不作为中间节点参与最小路径计算
INFRA_NODES = {"MONGO", "MYSQL", "METRICS", "WEBUI", "DNS"}
