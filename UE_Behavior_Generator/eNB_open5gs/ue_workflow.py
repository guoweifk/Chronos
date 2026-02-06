

# ue_workflow.py
import time
import threading
from queue import Queue
from datetime import datetime

def register_ues_with_rate(ues, ues_per_second):
    """
    按指定速率并发注册UE，并记录运行时间
    """
    
    interval = 1.0 / ues_per_second
    
    # 启动每个UE的注册线程
    for i, ue in enumerate(ues):
        def register_wrapper(ue_instance):
            try:
                # print(f"[注册] 开始注册 UE {ue_instance.imsi}")
                ue_instance.register()
                # print(f"[注册] UE {ue_instance.imsi} 注册请求发送完成")
            except Exception as e:
                print(f"[错误] UE {ue_instance.imsi} 注册失败: {e}")
                
        thread = threading.Thread(target=register_wrapper, args=(ue,))
        thread.start()
        time.sleep(interval)

def pdn_session_worker(registered_queue):
    """处理PDN会话建立的线程"""
    print("[PDN Worker] PDN会话建立线程已启动")
    while True:
        ue = registered_queue.get()
        if ue is None:  # 退出信号
            break
        try:
            ue.establish_pdn()
        except Exception as e:
            print(f"[PDN错误] UE {ue.imsi} PDN会话建立失败: {e}")


def sip_disconnect_worker(ims_pdn_disconnect_queue):
    """处理IMS PDN断开连接的线程"""
    print("[SIP Disconnect Worker] IMS PDN断开连接线程已启动")
    while True:
        ue = ims_pdn_disconnect_queue.get()
        if ue is None:  # 退出信号
            break
        try:
            print(f"[断开连接] 开始为UE {ue.imsi} 断开IMS PDN连接")
            ue.disconnect_ims_pdn()
        except Exception as e:
            print(f"[断开连接错误] UE {ue.imsi} IMS PDN连接断开失败: {e}")

def sip_register_worker(ims_pdn_queue):
    """处理SIP初始注册的线程"""
    print("[SIP Worker] SIP注册线程已启动")
    while True:
        ue = ims_pdn_queue.get()
        if ue is None:  # 退出信号
            break
        try:
            print(f"[SIP] 开始为UE {ue.imsi} 发送SIP注册")
            ue.send_sip_register_1()
        except Exception as e:
            print(f"[SIP错误] UE {ue.imsi} SIP注册发送失败: {e}")

def sip_second_register_worker(sip_401_queue):
    """处理SIP第二次注册的线程"""
    print("[SIP第二次注册] SIP二次注册线程已启动")
    while True:
        ue = sip_401_queue.get()
        if ue is None:  # 退出信号
            break
        try:
            print(f"[SIP二次] 开始为UE {ue.imsi} 发送第二次注册")
            ue.send_sip_register_2()
            print(f"[SIP二次] UE {ue.imsi} 第二次注册发送完成")
        except Exception as e:
            print(f"[SIP二次错误] UE {ue.imsi} 第二次注册失败: {e}")