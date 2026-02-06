# ue.py
import os
import copy
import socket
import time
import random
from myutils import *
from pycrate_asn1dir import S1AP
import eNAS
from eNB_LOCAL import *
from scapy.all import IP, UDP, TCP, Raw, send
from scapy.contrib.gtp import GTP_U_Header

class UE:
    sip_counter = 0
    def __init__(self, options, enb_session_dict, enb_client, enb_pdu, enb_instance):
        self.options = options
        self.imsi = options.imsi
        self.session_dict = modify_session_dict(copy.deepcopy(enb_session_dict), self.options)
        # 在初始化时分配 ENB-UE-S1AP-ID
        self.session_dict['ENB-UE-S1AP-ID'] = get_next_s1ap_id()
        # print(f"[UE {self.imsi}] 初始化 ENB-UE-S1AP-ID: {self.session_dict['ENB-UE-S1AP-ID']}")
        self.client = enb_client  # 与 eNB 共用连接
        self.PDU = enb_pdu        # 共用 PDU 模板
        self.enb = enb_instance  # 新增：保存eNB实例引用
        UE.sip_counter += 1
        # 有序生成 SIP 参数
        self.sip_tag = f"{UE.sip_counter:010d}"  # 10位数字，前导零填充
        self.sip_seq_number = 100000000 + UE.sip_counter  # 从100000001开始
        self.sip_call_id = f"{UE.sip_counter:020d}"  # 20位数字，前导零填充
        self.sip_nonce = None
        self.sip_response = None

    def _send_s1ap(self, s1ap_message):
        self.PDU.set_val(s1ap_message)
        message = self.PDU.to_aper()
        self.client = set_stream(self.client, 1)
        self.client.send(message)

    def register(self):
        # print(f"[UE {self.imsi}] === 开始注册 Attach ===")
        # 设置 GTP 管道（模拟网络栈）
        in_encap, out_encap = os.pipe()
        in_decap, out_decap = os.pipe()
        self.session_dict['PIPE-OUT-GTPU-ENCAPSULATE'] = out_encap
        self.session_dict['PIPE-OUT-GTPU-DECAPSULATE'] = out_decap
        self.session_dict['GTP-U'] = b'\x02'

        # 设置 NAS 附着请求
        self.session_dict['MME-IN-USE'] = 1
        self.session_dict['NAS'] = nas_attach_request(
            (self.session_dict['SESSION-TYPE'], self.session_dict['SESSION-SESSION-TYPE']),
            self.session_dict['ATTACH-PDN'],
            self.session_dict['MOBILE-IDENTITY'],
            self.session_dict['PDP-TYPE'],
            self.session_dict['ATTACH-TYPE'],
            self.session_dict['TMSI'],
            self.session_dict['LAI'],
            self.session_dict['SMS-UPDATE-TYPE'],
            self.session_dict['PCSCF-RESTORATION'],
            self.session_dict['PDN-CONNECTIVITY-REQUEST-TYPE'],
        )
        self.session_dict['SQN'] = 0
        # self.session_dict['ENB-UE-S1AP-ID'] = get_next_s1ap_id()
        # 发送 S1AP InitialUEMessage
        self._send_s1ap(InitialUEMessage(self.session_dict))
        # 接下来需要监听端口。处理响应包

        # print(f"[UE {self.imsi}] === Attach 注册完成 ===")

    # 可选：PDN 连接建立
    def establish_pdn(self):
        self.session_dict["APN"] = "ims"
        if self.session_dict['STATE'] > 1:
            if self.session_dict['MME-UE-S1AP-ID'] > 0:
                self.session_dict = ProcessUplinkNAS("pdn connectivity request", self.session_dict)
                self._send_s1ap(UplinkNASTransport(self.session_dict))
            else:
                self.session_dict = print_log(self.session_dict, "NAS: Unable to send PDNConnectivityRequest. No S1. Send ServiceRequest first.")
        else:
            self.session_dict = print_log(self.session_dict, "NAS: Unable to send PDNConnectivityRequest. State < 2")
        # self.PDU, self.client, self.session_dict = ProcessS1AP(self.PDU, self.client, self.session_dict, 1)
        # print(self.session_dict)

    # # 可选：重新建立 IMS 会话
    # def rebuild_ims_pdn(self):
    #     if self.session_dict['STATE'] > 1 and self.session_dict['MME-UE-S1AP-ID'] > 0:
    #         self.session_dict = ProcessUplinkNAS("pdn disconnect request", self.session_dict)
    #         self._send_s1ap(UplinkNASTransport(self.session_dict))
    #         self.PDU, self.client, self.session_dict = ProcessS1AP(self.PDU, self.client, self.session_dict, 1)
    #         # 重建
    #         self.session_dict = ProcessUplinkNAS("pdn connectivity request", self.session_dict)
    #         self._send_s1ap(UplinkNASTransport(self.session_dict))
    #         # self.PDU, self.client, self.session_dict = ProcessS1AP(self.PDU, self.client, self.session_dict, 1)
    #     # print(self.session_dict)

    def disconnect_ims_pdn(self):
        if self.session_dict['STATE'] > 1 and self.session_dict['MME-UE-S1AP-ID'] > 0:
            self.session_dict = ProcessUplinkNAS("pdn disconnect request", self.session_dict)
            self._send_s1ap(UplinkNASTransport(self.session_dict))

    def print_session(self):
        print("==================================================")
        # print(f"[UE {self.imsi}] Session Dict: {self.session_dict}")
        print("==================================================")
        print(f"[UE {self.imsi}] Session Summary:")
        
        imsi = self.session_dict.get("IMSI", "N/A")
        pdn_ipv4 = self.session_dict.get("PDN-ADDRESS-IPV4", "N/A")
        pcscf_ipv4 = self.session_dict.get("P-CSCF-IPv4", "N/A")

        # 取第一个 SGW-GTP-ADDRESS（已是 bytes），转为点分十进制
        sgw_gtp = self.session_dict.get("SGW-GTP-ADDRESS", [])
        if sgw_gtp and isinstance(sgw_gtp[0], bytes):
            sgw_gtp_ip = socket.inet_ntoa(sgw_gtp[0])
        else:
            sgw_gtp_ip = "N/A"

        # 取第一个 SGW TEID（4 字节），转为整数
        sgw_teid = self.session_dict.get("SGW-TEID", [])
        if sgw_teid and isinstance(sgw_teid[-1], bytes):
            teid_int = int.from_bytes(sgw_teid[-1], byteorder="big")
        else:
            teid_int = "N/A"

        print(f"  IMSI             : {imsi}")
        print(f"  PDN IPv4 Addr    : {pdn_ipv4}")
        print(f"  P-CSCF IPv4      : {pcscf_ipv4}")
        print(f"  SGW GTP Addr     : {sgw_gtp_ip}")
        print(f"  SGW TEID         : {teid_int}")



    def send_sip_register_1(self):
            """发送第一个 SIP REGISTER 消息（无鉴权）"""
            if "PDN-ADDRESS-IPV4" not in self.session_dict:
                print(f"[UE {self.imsi}] 缺少 PDN IP 地址，无法发送 SIP REGISTER")
                return False
                
            # 获取必要的参数
            pdn_ip = self.session_dict["PDN-ADDRESS-IPV4"]
            pcscf_ipv4 = self.session_dict.get("P-CSCF-IPv4", "N/A")
            # 构建内层 SIP REGISTER 消息
            inner_payload = self._create_sip_register_1_payload(pdn_ip, pcscf_ipv4)
            # 发送 GTP-U 数据包
            self.send_gtp_u_packet(inner_payload)
            print(f"[UE {self.imsi}] 已发送第一个 SIP REGISTER 到 P-CSCF {pcscf_ipv4}")
            return True

    def _create_sip_register_1_payload(self, pdn_ip, pcscf_ip):
        """创建第一个 SIP REGISTER 消息的内层负载"""
        # 生成随机的源端口
        src_port = 20000 + (int(time.time()) % 20000)
        dst_port = 5060  # SIP 标准端口
        
        # 构建 SIP REGISTER 消息（完全匹配 create_sip_register_1 函数）
        sip_msg = (
            f"REGISTER sip:ims.mnc003.mcc505.3gppnetwork.org SIP/2.0\r\n"
            f"From: <sip:{self.imsi}@ims.mnc003.mcc505.3gppnetwork.org>;tag={self.sip_tag}\r\n"
            f"To: <sip:{self.imsi}@ims.mnc003.mcc505.3gppnetwork.org>\r\n"
            f"CSeq: {self.sip_seq_number} REGISTER\r\n"
            f"Call-ID: {self.sip_call_id}@{pdn_ip}\r\n"
            "Max-Forwards: 70\r\n"
            f"Contact: <sip:{self.imsi}@{pdn_ip}:{src_port}>;+g.3gpp.accesstype=\"cellular2\";audio;+g.3gpp.smsip;+g.3gpp.icsi-ref=\"urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel\";+sip.instance=\"<urn:gsma:imei:86196306-254962-0>\"\r\n"
            f"Via: SIP/2.0/UDP {pdn_ip}:{src_port};branch=z9hG4bKBRANCH{self.sip_tag[-6:]}\r\n"
            "Expires: 600000\r\n"
            "Require: sec-agree\r\n"
            "Proxy-Require: sec-agree\r\n"
            "Supported: path,sec-agree\r\n"
            "Allow: INVITE,BYE,CANCEL,ACK,NOTIFY,UPDATE,PRACK,INFO,MESSAGE,OPTIONS\r\n"
            f"Authorization: Digest uri=\"sip:ims.mnc003.mcc505.3gppnetwork.org\",username=\"{self.imsi}@ims.mnc003.mcc505.3gppnetwork.org\",response=\"\",realm=\"ims.mnc003.mcc505.3gppnetwork.org\",nonce=\"\"\r\n"
            "User-Agent: Xiaomi_Redmi K40S_V13.0.11.0.SLMCNXM\r\n"
            "Content-Length: 0\r\n\r\n"
        ).encode('utf-8')
        
        # 构建完整的传输层+应用层包
        udp_header = UDP(sport=src_port, dport=dst_port)
        return IP(src=pdn_ip, dst=pcscf_ip) / udp_header / Raw(load=sip_msg)

    # 在UE类中添加以下方法

    def send_sip_register_2(self):
        """发送第二个 SIP REGISTER 消息（带鉴权）"""
        if "PDN-ADDRESS-IPV4" not in self.session_dict:
            print(f"[UE {self.imsi}] 缺少 PDN IP 地址，无法发送第二个 SIP REGISTER")
            return False
        
        # 检查是否有nonce（从401响应中获得）
        if not self.sip_nonce:
            print(f"[UE {self.imsi}] 缺少 nonce，无法发送第二个 SIP REGISTER")
            return False
            
        # 检查是否有response（鉴权响应）
        if not self.sip_response:
            print(f"[UE {self.imsi}] 缺少 response，无法发送第二个 SIP REGISTER")
            return False
            
        # 获取必要的参数
        pdn_ip = self.session_dict["PDN-ADDRESS-IPV4"]
        pcscf_ipv4 = self.session_dict.get("P-CSCF-IPv4", "N/A")
        
        # 构建内层 SIP REGISTER 消息（带鉴权）
        inner_payload = self._create_sip_register_2_payload(pdn_ip, pcscf_ipv4)
        
        # 发送 GTP-U 数据包
        self.send_gtp_u_packet(inner_payload)
        print(f"[UE {self.imsi}] 已发送第二个 SIP REGISTER（带鉴权）到 P-CSCF {pcscf_ipv4}")
        return True

    def _create_sip_register_2_payload(self, pdn_ip, pcscf_ip):
        """创建第二个 SIP REGISTER 消息的内层负载（带鉴权）"""
        # 生成随机的源端口
        src_port = 20000 + (int(time.time()) % 20000)
        dst_port = 5060  # SIP 标准端口
        
        # 构建 SIP REGISTER 消息（带鉴权信息）
        sip_msg = (
            f"REGISTER sip:ims.mnc003.mcc505.3gppnetwork.org SIP/2.0\r\n"
            f"From: <sip:{self.imsi}@ims.mnc003.mcc505.3gppnetwork.org>;tag={self.sip_tag}\r\n"
            f"To: <sip:{self.imsi}@ims.mnc003.mcc505.3gppnetwork.org>\r\n"
            f"CSeq: {self.sip_seq_number+1} REGISTER\r\n"
            f"Call-ID: {self.sip_call_id}@{pdn_ip}\r\n"
            f"Via: SIP/2.0/UDP {pdn_ip}:{src_port};branch=z9hG4bKBRANCH{self.sip_tag[-6:]}\r\n"
            "Max-Forwards: 70\r\n"
            f"Contact: <sip:{self.imsi}@{pdn_ip}:{src_port}>;+g.3gpp.accesstype=\"cellular2\";+sip.instance=\"<urn:gsma:imei:86196306-254962-0>\";audio;+g.3gpp.smsip;+g.3gpp.icsi-ref=\"urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel\"\r\n"
            "P-Access-Network-Info: 3GPP-E-UTRAN-FDD;utran-cell-id-3gpp=4669200010019B01\r\n"
            "Expires: 600000\r\n"
            "Require: sec-agree\r\n"
            "Proxy-Require: sec-agree\r\n"
            "Supported: path,sec-agree\r\n"
            "Allow: INVITE,BYE,CANCEL,ACK,NOTIFY,UPDATE,PRACK,INFO,MESSAGE,OPTIONS\r\n"
            f"Authorization: Digest username=\"{self.imsi}@ims.mnc003.mcc505.3gppnetwork.org\",realm=\"ims.mnc003.mcc505.3gppnetwork.org\",uri=\"sip:ims.mnc003.mcc505.3gppnetwork.org\",qop=auth,nonce=\"{self.sip_nonce}\",nc=00000001,cnonce=\"4149304045\",algorithm=AKAv1-MD5,response=\"{self.sip_response}\"\r\n"
            "User-Agent: Xiaomi_Redmi K40S_V13.0.11.0.SLMCNXM\r\n"
            "Content-Length: 0\r\n\r\n"
        ).encode('utf-8')
        
        # 构建完整的传输层+应用层包
        udp_header = UDP(sport=src_port, dport=dst_port)
        return IP(src=pdn_ip, dst=pcscf_ip) / udp_header / Raw(load=sip_msg)

    def send_gtp_u_packet(self, inner_payload=None):  # 修改：替换原有方法
        """构建并发送 GTP-U 数据包到 SGW"""
        if not self._validate_session_for_gtp():
            print(f"[UE {self.imsi}] 缺少必要的 GTP 隧道参数，无法发送 GTP-U 包")
            return False       
        sgw_ip = socket.inet_ntoa(self.session_dict["SGW-GTP-ADDRESS"][-1])
        gtp_data = self._build_gtp_u_data(inner_payload)
        # 使用eNB的统一套接字发送
        success = self.enb.send_gtp_u_packet(sgw_ip, gtp_data)
        if success:
            teid = int.from_bytes(self.session_dict["SGW-TEID"][-1], 'big')
            print(f"[UE {self.imsi}] GTP-U数据包已通过eNB发送到 {sgw_ip}, TEID={teid}")
        return success

    def _validate_session_for_gtp(self):
        """验证会话中是否有必要的 GTP 参数"""
        required_keys = [
            "SGW-GTP-ADDRESS", "SGW-TEID", 
            "PDN-ADDRESS-IPV4", "P-CSCF-IPv4"
        ]
        for key in required_keys:
            # 检查键是否存在且值有效
            if key not in self.session_dict:
                return False
            if key in ["SGW-GTP-ADDRESS", "SGW-TEID"]:
                if not self.session_dict[key] or not self.session_dict[key][0]:
                    return False
        return True
    
    def _build_gtp_u_data(self, inner_payload):
        """构建GTP-U数据部分（不含外层IP/UDP头）"""
        if not inner_payload:
            return b''
        teid = int.from_bytes(self.session_dict["SGW-TEID"][-1], 'big')
        # 构建GTP-U头部
        gtp_header = GTP_U_Header(
            version=1,
            PT=1,
            E=0,
            S=0,
            PN=0,
            gtp_type=0xFF,
            teid=teid
        )
        # 返回 GTP-U头 + 内层IP包 的字节数据
        gtp_packet = gtp_header / inner_payload
        return bytes(gtp_packet)
        
    
    