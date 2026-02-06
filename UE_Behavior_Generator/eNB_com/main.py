# main.py - 精简版多进程LTE网络仿真器
import multiprocessing as mp
import time
from dataclasses import dataclass
from typing import List

from enb import ENB
from myutils import generate_options


@dataclass
class BaseStationConfig:
    """基站配置"""
    enb_id: str
    enb_name: str
    enb_ip: str
    mme_ip: str
    num_ues: int
    ues_per_second: int
    imsi_base: str
    macroENB_ID: int  # 新增：数值型eNB ID，用于ENB对象创建
    udp_port: int = 2152  # 每个基站的UDP监听端口


class BaseStationManager:
    """基站管理类"""
    
    def __init__(self, config: BaseStationConfig):
        self.config = config
        self.process = None
    
    def start(self):
        """启动基站进程"""
        self.process = mp.Process(
            target=self._run_base_station,
            args=(self.config,)
        )
        self.process.start()
        return True
    
    def stop(self):
        """停止基站进程"""
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join()
    
    @staticmethod
    def _run_base_station(config: BaseStationConfig):
        """基站进程主函数"""
        import threading
        from queue import Queue
        from ue import UE
        from s1ap_handler import MultiThreadedS1APHandler
        from sip_listener import UDP2152Listener
        from ue_workflow import (
            register_ues_with_rate, pdn_session_worker, 
            sip_disconnect_worker, sip_register_worker, 
            sip_second_register_worker
        )
        
        # 生成UE配置
        options_list = generate_options(
            imsi_base=config.imsi_base,
            num_options=config.num_ues,
            enbIP=config.enb_ip,
            mmeIP=config.mme_ip
        )
        
        # 创建并启动eNB - 传入数值型eNB ID作为最后一个参数
        enb = ENB(config.enb_name, options_list[0], config.macroENB_ID)
        enb.connect_to_mme()
        enb.s1_setup()
        
        print(f"[{config.enb_name}] 基站启动完成，IP: {config.enb_ip}, eNB ID: {config.macroENB_ID}")
        
        # 创建UE实例并初始化映射字典
        ues = []
        ue_dict = {}
        registered_queue = Queue()
        registered_ue_dict = {}
        ims_pdn_queue = Queue()
        ims_pdn_ue_dict = {}
        sip_401_queue = Queue()
        sip_401_ue_dict = {}
        imsi_ue_dict = {}
        ims_pdn_disconnect_queue = Queue()
        
        for opts in options_list:
            ue = UE(opts, enb.session_dict, enb.client, enb.PDU, enb)
            ues.append(ue)
            # 建立映射关系
            enb_ue_id = ue.session_dict['ENB-UE-S1AP-ID']
            ue_dict[enb_ue_id] = [ue, 0, 0, 0]
            imsi_ue_dict[ue.imsi] = ue
        
        # 启动S1AP消息处理器
        handler = MultiThreadedS1APHandler(
            enb.client, ue_dict, registered_ue_dict, registered_queue,
            ims_pdn_ue_dict, ims_pdn_queue, max_workers=128
        )
        
        # 启动UDP监听器 - 绑定到基站的特定IP地址
        udp_listener = UDP2152Listener(
            port=config.udp_port,
            host=config.enb_ip,  # 关键修改：绑定到基站IP而非0.0.0.0
            imsi_ue_dict=imsi_ue_dict,
            sip_401_queue=sip_401_queue,
            ims_pdn_disconnect_queue=ims_pdn_disconnect_queue
        )
        udp_listener.start()
        
        # 启动PDN会话工作线程
        pdn_thread = threading.Thread(target=pdn_session_worker, args=(registered_queue,))
        pdn_thread.daemon = True
        pdn_thread.start()
        
        # 启动IMS PDN断开连接工作线程
        disconnect_thread = threading.Thread(target=sip_disconnect_worker, args=(ims_pdn_disconnect_queue,))
        disconnect_thread.daemon = True
        disconnect_thread.start()
        
        # 启动SIP注册工作线程
        sip_thread = threading.Thread(target=sip_register_worker, args=(ims_pdn_queue,))
        sip_thread.daemon = True
        sip_thread.start()
        
        # 启动SIP第二次注册工作线程
        sip_second_thread = threading.Thread(target=sip_second_register_worker, args=(sip_401_queue,))
        sip_second_thread.daemon = True
        sip_second_thread.start()
        
        # 开始注册UE
        register_thread = threading.Thread(
            target=register_ues_with_rate, 
            args=(ues, config.ues_per_second)
        )
        register_thread.daemon = True
        register_thread.start()
        
        print(f"[{config.enb_name}] UE注册开始，{config.num_ues}个UE，速率{config.ues_per_second}/秒")
        print(f"[{config.enb_name}] UDP监听器已启动，监听 {config.enb_ip}:{config.udp_port}")
        
        # 保持进程运行
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            handler.stop()
            udp_listener.stop()
            print(f"[{config.enb_name}] 基站进程退出")


class NetworkSimulator:
    """网络仿真器类"""
    
    def __init__(self):
        self.base_stations = {}
    
    def add_base_station(self, config: BaseStationConfig):
        """添加基站"""
        manager = BaseStationManager(config)
        self.base_stations[config.enb_id] = manager
    
    def start_all(self):
        """启动所有基站"""
        for manager in self.base_stations.values():
            manager.start()
            time.sleep(1)  # 避免同时连接MME
    
    def stop_all(self):
        """停止所有基站"""
        for manager in self.base_stations.values():
            manager.stop()
    
    def run(self):
        """运行仿真器"""
        self.start_all()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            self.stop_all()


def create_configs() -> List[BaseStationConfig]:
    """创建基站配置"""
    return [
        BaseStationConfig(
            enb_id="enb_001",
            enb_name="ZH1-eNB", 
            enb_ip="192.168.55.40",
            mme_ip="192.168.55.43",
            num_ues=10000,
            ues_per_second=1,
            imsi_base="466920123456001",
            macroENB_ID=1  
        )
        # BaseStationConfig(
        #     enb_id="enb_002",
        #     enb_name="ZH2-eNB",
        #     enb_ip="192.168.56.159", 
        #     mme_ip="192.168.8.212",
        #     num_ues=1000,
        #     ues_per_second=10,
        #     imsi_base="505030000001001",
        #     macroENB_ID=2  
        # ),
        # BaseStationConfig(
        #     enb_id="enb_003", 
        #     enb_name="ZH3-eNB",
        #     enb_ip="192.168.56.160",
        #     mme_ip="192.168.8.212",
        #     num_ues=1000,
        #     ues_per_second=10,
        #     imsi_base="505030000002001",
        #     macroENB_ID=3  
        # ),
        # BaseStationConfig(
        #     enb_id="enb_004", 
        #     enb_name="ZH4-eNB",
        #     enb_ip="192.168.56.161",
        #     mme_ip="192.168.8.212", 
        #     num_ues=1000,
        #     ues_per_second=10,
        #     imsi_base="505030000003001",
        #     macroENB_ID=4  
        # ),
        # BaseStationConfig(
        #     enb_id="enb_005",
        #     enb_name="ZH5-eNB",
        #     enb_ip="192.168.56.162",
        #     mme_ip="192.168.8.212",
        #     num_ues=1000,
        #     ues_per_second=10,
        #     imsi_base="505030000004001",
        #     macroENB_ID=5
        # ),
        # BaseStationConfig(
        #     enb_id="enb_006",
        #     enb_name="ZH6-eNB",
        #     enb_ip="192.168.56.163",
        #     mme_ip="192.168.8.212",
        #     num_ues=1000,
        #     ues_per_second=10,
        #     imsi_base="505030000005001",
        #     macroENB_ID=6  
        # ),
        # BaseStationConfig(
        #     enb_id="enb_007",
        #     enb_name="ZH7-eNB",
        #     enb_ip="192.168.56.164",
        #     mme_ip="192.168.8.212",
        #     num_ues=1000,
        #     ues_per_second=10,
        #     imsi_base="505030000006001",
        #     macroENB_ID=7  
        # ),
        # BaseStationConfig(
        #     enb_id="enb_008",
        #     enb_name="ZH8-eNB",
        #     enb_ip="192.168.56.165",
        #     mme_ip="192.168.8.212",
        #     num_ues=1000,
        #     ues_per_second=10,
        #     imsi_base="505030000007001",
        #     macroENB_ID=8  
        # ),
        # BaseStationConfig(
        #     enb_id="enb_009",
        #     enb_name="ZH9-eNB",
        #     enb_ip="192.168.56.166",
        #     mme_ip="192.168.8.212",
        #     num_ues=1000,
        #     ues_per_second=10,
        #     imsi_base="505030000008001",
        #     macroENB_ID=9  
        # ),
        # BaseStationConfig(
        #     enb_id="enb_010",
        #     enb_name="ZH10-eNB",
        #     enb_ip="192.168.56.167",
        #     mme_ip="192.168.8.212",
        #     num_ues=1000,
        #     ues_per_second=10,
        #     imsi_base="505030000009001",
        #     macroENB_ID=10  
        # )
    ]


def main():
    """主函数"""
    print("启动多进程LTE仿真器...")
    
    mp.set_start_method('spawn', force=True)
    # 创建仿真器
    simulator = NetworkSimulator()
    
    # 添加基站
    for config in create_configs():
        simulator.add_base_station(config)
    
    # 运行
    simulator.run()


if __name__ == "__main__":
    main()