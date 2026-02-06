# file: enb.py
import socket
import copy
from pycrate_asn1dir import S1AP
from myutils import init_section_dict, setup_s1_connection, session_dict_initialization, ip2int
import struct


class ENB:
    def __init__(self, enb_name, options, macroENB_ID):
        self.enb_name = enb_name
        self.options = options
        self.client = None
        self.session_dict = None
        self.PDU = S1AP.S1AP_PDU_Descriptions.S1AP_PDU
        self.gtp_u_socket = None  # GTP-U发送套接字
        self.macroENB_ID = macroENB_ID

    def create_gtp_u_socket(self):
        """创建GTP-U发送套接字"""
        if self.gtp_u_socket is None:
            self.gtp_u_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 关键修复：绑定到基站的特定IP地址
            self.gtp_u_socket.bind((self.options.eNB_ip, 0))
            print(f"[eNB] 创建GTP-U套接字成功，绑定到IP: {self.options.eNB_ip}")
        return self.gtp_u_socket
    
    def send_gtp_u_packet(self, sgw_ip, gtp_data):
        """统一的GTP-U数据包发送接口"""
        if self.gtp_u_socket is None:
            self.create_gtp_u_socket()
        try:
            self.gtp_u_socket.sendto(gtp_data, (sgw_ip, 2152))
            return True
        except Exception as e:
            print(f"[eNB] GTP-U发送失败: {e}")
            return False
        
    def connect_to_mme(self):
        """建立到 MME 的 SCTP 连接"""
        print(f"[eNB] Connecting to MME at {self.options.mme_ip}...")
        server_address = (self.options.mme_ip, 36412)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP)
        sock.bind((self.options.eNB_ip, 0))
        param = bytearray(sock.getsockopt(132, 10, 32))
        param[11] = 18  # 这个就是所谓的PPID。得有，不然千通的MME会报错
        # param[11] = 255# 设置最大流数为 65535 
        sock.setsockopt(132, 10, param)
        sock.connect(server_address)
        self.client = sock
        print(f"[eNB] SCTP Connected to {server_address}")

    def s1_setup(self):
        """执行 S1 Setup 并保存基站状态"""
        print("[eNB] Sending S1SetupRequest...")
        sess = copy.deepcopy(init_section_dict(self.options))
        sess = session_dict_initialization(sess)
        sess['ENB-NAME'] = self.enb_name

        # 设置 GTP 地址
        gtp_ip = self.options.gtp_u_ip or self.options.eNB_ip
        sess['ENB-GTP-ADDRESS-INT'] = ip2int(gtp_ip)
        sess['ENB-GTP-ADDRESS'] = socket.inet_aton(gtp_ip)
        sess['ENB-ID'] = self.macroENB_ID
        self.PDU, self.client, sess = setup_s1_connection(self.PDU, self.client, sess)
        self.session_dict = sess
        print(f"[eNB] S1Setup Done, STATE = {sess.get('STATE')}")