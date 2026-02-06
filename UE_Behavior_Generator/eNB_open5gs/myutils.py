import sys, os
import datetime
from eNB_LOCAL import *
import socket
from pycrate_asn1dir import S1AP
from binascii import hexlify, unhexlify
import os
from types import SimpleNamespace
import eNAS
from eMENU import print_log
import time
import copy
import subprocess
import threading

# global variables
global_ue_s1ap_id_counter = 1
s1ap_id_lock = threading.Lock()
PLMN = "46692"

def generate_options(imsi_base, num_options,enbIP, mmeIP):
    # 生成一批模拟用户的配置（IMSI、eNB IP、MME IP、密钥等）
    options_list = []
    for i in range(num_options):
        options = SimpleNamespace(
            # eNB_ip="172.22.0.100",
            # mme_ip="172.22.0.9",
            eNB_ip=enbIP,
            mme_ip=mmeIP,
            gateway_ip_address=None,
            serial_interface=None,
            imsi=str(int(imsi_base) + i),
            imei="4901542032375186",
            ki="8baf473f2f8fd09487cccbd7097c6862",
            op=None,
            opc="E8ED289DEBA952E4283B54E88E618ABC",
            plmn="46692",
            tac1="1",
            tac2=None,
            gtp_kernel=False,
            maxseg=None,
            ueradiocapability=None,
            guti=None,
            mme_2_ip=None,
            gtp_u_ip=None,
            apn="ims"
        )
        options_list.append(options)
    return options_list







def get_next_s1ap_id():
    """线程安全地获取下一个唯一的 S1AP ID"""
    global global_ue_s1ap_id_counter
    with s1ap_id_lock:
        current_id = global_ue_s1ap_id_counter
        global_ue_s1ap_id_counter += 1
    print(f"分配 ENB-UE-S1AP-ID: {current_id}")
    return current_id



def init_section_dict(options):
    session_dict = {}
    session_dict['GATEWAY'] = options.gateway_ip_address
    if not options.mme_ip:
        print('MME IP Required. Exiting.')
        exit(1)
    if not options.eNB_ip:
        print('eNB Local IP Required! Exiting.')
        exit(1)

    session_dict = {}

    if options.gateway_ip_address:
        subprocess.call(f"route add {options.mme_ip}/32 gw {options.gateway_ip_address}", shell=True)
        session_dict['GATEWAY'] = options.gateway_ip_address
    else:
        session_dict['GATEWAY'] = None

    # 认证配置
    session_dict['LOCAL_KEYS'] = options.serial_interface is None
    if not session_dict['LOCAL_KEYS']:
        session_dict['SERIAL-INTERFACE'] = options.serial_interface
        session_dict['LOCAL_MILENAGE'] = False

    # 用户身份配置
    session_dict['IMSI'] = options.imsi
    session_dict['IMEISV'] = options.imei

    # 密钥配置
    if options.ki and (options.op or options.opc):
        session_dict['LOCAL_KEYS'] = False
        session_dict['LOCAL_MILENAGE'] = True
        session_dict['KI'] = unhexlify(options.ki)
        if options.op:
            session_dict['OP'] = unhexlify(options.op)
            session_dict['OPC'] = None
        elif options.opc:
            session_dict['OPC'] = unhexlify(options.opc)
            session_dict['OP'] = None
    else:
        session_dict['LOCAL_MILENAGE'] = False

    # TAC配置
    session_dict['ENB-TAC1'] = int(options.tac1).to_bytes(2, byteorder='big') if options.tac1 else None
    session_dict['ENB-TAC2'] = int(options.tac2).to_bytes(2, byteorder='big') if options.tac2 else None

    # PLMN配置
    session_dict['PLMN'] = options.plmn if options.plmn else PLMN

    # GTP内核配置
    if options.gtp_kernel:
        session_dict['GTP-KERNEL'] = True
        subprocess.call("modprobe gtp", shell=True)
        subprocess.call("gtp-link del gtp1", shell=True)
        subprocess.call("killall gtp-tunnel", shell=True)
        subprocess.call("killall gtp-link", shell=True)
    else:
        session_dict['GTP-KERNEL'] = False

    # UE能力配置
    session_dict['UE-RADIO-CAPABILITY'] = unhexlify(options.ueradiocapability) if options.ueradiocapability else None

    if options.guti:
        aux = options.guti.split('-')
        session_dict['ENCODED-GUTI'] = eNAS.encode_guti(aux[0], int(aux[1]), int(aux[2]), int(aux[3]))
    else:
        session_dict['ENCODED-GUTI'] = None

    # APN配置
    # session_dict['APN'] = options.apn

    if options.gtp_u_ip:
        session_dict['ENB-GTP-ADDRESS-INT'] = ip2int(options.gtp_u_ip)
    else:
        session_dict['ENB-GTP-ADDRESS-INT'] = ip2int(options.eNB_ip)
    session_dict['ENB-GTP-ADDRESS'] = socket.inet_aton(options.eNB_ip)

    session_dict['MME-IN-USE'] = 1
    return session_dict


def setup_s1_connection(PDU, client, session_dict):
    """
    执行S1Setup过程，只执行一次
    返回更新后的PDU, client, session_dict状态
    """
    print("开始执行S1Setup...")
    # 15 code - S1SetupRequest
    PDU.set_val(S1SetupRequest(session_dict))
    message = PDU.to_aper()
    client = set_stream(client, 0)
    bytes_sent = client.send(message)
    print("S1AP: sending S1SetupRequest")
    # 处理S1Setup响应
    PDU, client, session_dict = ProcessS1AP(PDU, client, session_dict, 1)
    print(f"S1Setup完成，STATE: {session_dict.get('STATE', 'Unknown')}")
    return PDU, client, session_dict


def modify_session_dict(session_dict, options):
    session_dict['IMSI'] = options.imsi
    session_dict['APN'] = "internet"
    session_dict['ENCODED-IMSI'] = eNAS.encode_imsi(session_dict['IMSI'])
    session_dict['MOBILE-IDENTITY'] = session_dict['ENCODED-IMSI']
    return session_dict


def hexdump(src, length=16):
        result = []
        digits = 4 if isinstance(src, str) else 2

        for i in range(0, len(src), length):
            s = src[i:i+length]
            hexa = ' '.join(f"{b:02x}" for b in s)
            text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in s)
            result.append(f"{i:08x}  {hexa:<48}  {text}")
        return '\n'.join(result)