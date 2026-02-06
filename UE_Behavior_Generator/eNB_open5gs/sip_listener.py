import socket
import threading
import time
import re
from sip_response_calculator import calculate_response
from typing import Optional
class UDP2152Listener:
    def __init__(self, port=2152, host='0.0.0.0', imsi_ue_dict=None, sip_401_queue=None,ims_pdn_disconnect_queue=None):
        """
        初始化UDP监听器
        :param port: 监听端口，默认2152
        :param host: 监听地址，默认监听所有接口
        :param imsi_ue_dict: IMSI到UE对象的映射字典
        :param sip_401_queue: 401响应处理队列
        """
        self.port = port
        self.host = host
        self.socket = None
        self.running = False
        self.thread = None
        self.imsi_ue_dict = imsi_ue_dict or {}  # 新增
        self.sip_401_queue = sip_401_queue     # 新增
        self.ims_pdn_disconnect_queue = ims_pdn_disconnect_queue  # 新增
        print(f"[UDP Listener] 初始化UDP监听器，端口: {port}")
    
    def start(self):
        """启动UDP监听线程"""
        if self.running:
            print("[UDP Listener] 监听器已经在运行中")
            return
        try:
            # 创建UDP套接字
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 绑定端口
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(1.0)  # 设置1秒超时，用于优雅退出
            
            print(f"[UDP Listener] 成功绑定到 {self.host}:{self.port}")
            
            # 启动监听线程
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop)
            self.thread.daemon = True
            self.thread.start()
            
            print("[UDP Listener] 监听线程已启动")
            
        except Exception as e:
            print(f"[UDP Listener] 启动失败: {e}")
            self.running = False
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def _listen_loop(self):
        """监听循环，在独立线程中运行"""
        print(f"[UDP Listener] 开始监听UDP端口 {self.port}")
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)  
                self._handle_packet(data, addr)
                
            except socket.timeout:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                if self.running:  # 只有在运行状态下才打印错误
                    print(f"[UDP Listener] 接收数据包时出错: {e}")
                break
        
        print("[UDP Listener] 监听循环已退出")
    
    def _handle_packet(self, data, addr):
        """
        处理接收到的数据包
        :param data: 接收到的数据
        :param addr: 发送方地址
        """
        try:
            print(f"\n[UDP Listener] 收到来自 {addr[0]}:{addr[1]} 的数据包")
            print(f"[UDP Listener] 数据包长度: {len(data)} 字节")
            
            # 尝试解码为SIP消息
            try:
                response = data.decode('utf-8', errors='ignore')
                if 'SIP/2.0' in response:
                    self._process_sip_response(response, addr)
                else:
                    # 非SIP消息，打印十六进制数据
                    print(f"[UDP Listener] 非SIP数据包，十六进制: {data.hex()}")
            except Exception as e:
                print(f"[UDP Listener] 解码数据包时出错: {e}")
                print(f"[UDP Listener] 原始十六进制: {data.hex()}")
            
            print("-" * 60)
            
        except Exception as e:
            print(f"[UDP Listener] 处理数据包时出错: {e}")
    
    def _extract_imsi_from_sip(self, response: str) -> Optional[str]:
        """从SIP消息头部提取IMSI"""
        m_from = re.search(r"From:\s*<sip:(\d+)@", response)
        return m_from.group(1) if m_from else None
    
    def _process_sip_response(self, response: str, addr):
        """
        处理SIP响应消息
        :param response: SIP响应内容
        :param addr: 发送方地址
        """
        try:
            imsi = self._extract_imsi_from_sip(response)
            if not imsi:
                print(f"[UDP Listener] 无法从SIP消息中提取IMSI")
                return
            sip_pattern = r'SIP/2\.0\s+(\d{3})'
            match = re.search(sip_pattern, response)
            if match:
                status_code = match.group(1)
                print(f"提取到状态码: {status_code}")
            # 根据状态码进行不同处理
            if status_code == "100":
                print(f"[{imsi}] 收到了 100 Trying")
                
            elif status_code == "401":
                # 提取nonce
                m_nonce = re.search(r'nonce="([^"]+)"', response)
                nonce = m_nonce.group(1) if m_nonce else None
                if nonce:
                    print(f"[{imsi}] 收到401响应，nonce为: {nonce}")  
                    # 检查UE是否存在并直接处理
                    ue = self.imsi_ue_dict.get(imsi)                  
                    try:
                        # 计算响应值并设置UE参数
                        ue.sip_nonce = nonce
                        ue.sip_response = calculate_response(imsi, nonce)
                        print(f"[{imsi}] 已计算响应值，准备发送第二次注册")
                        # 将已处理的UE对象放入队列
                        if self.sip_401_queue:
                            self.sip_401_queue.put(ue)
                            print(f"[{imsi}] UE已加入第二次注册队列")
                        else:
                            print(f"[{imsi}] 401处理队列未配置")
                    except Exception as e:
                        print(f"[{imsi}] 处理401响应时出错: {e}")
                else:
                    print(f"[{imsi}] 收到401但未找到nonce")
            elif status_code == "200":
                print(f"[{imsi}] 收到200 OK，注册成功")
            elif status_code == "504" or status_code == "500":
                print(f"[{imsi}] 收到 {status_code} 响应，可能是服务器忙或不可用")
                ue = self.imsi_ue_dict.get(imsi)
                try:
                    if self.ims_pdn_disconnect_queue:
                        self.ims_pdn_disconnect_queue.put(ue)
                        print(f"[{imsi}] UE已加入断开连接队列")
                    else:
                        print(f"[{imsi}] 断开连接队列未配置")
                except Exception as e:
                    print(f"[{imsi}] 添加到断开连接队列时出错: {e}")

            else:
                print(f"[{imsi}] 未处理的响应码: {status_code}")
                
        except Exception as e:
            print(f"[UDP Listener] 处理SIP响应时出错: {e}")
            print(f"[UDP Listener] 原始响应: {response[:200]}...")

    def stop(self):
        """停止UDP监听器"""
        if not self.running:
            print("[UDP Listener] 监听器已经停止")
            return
        
        print("[UDP Listener] 正在停止监听器...")
        self.running = False
        
        # 关闭套接字
        if self.socket:
            self.socket.close()
            self.socket = None
        
        # 等待线程结束
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)
        
        print("[UDP Listener] 监听器已停止")
    
    def is_running(self):
        """检查监听器是否正在运行"""
        return self.running and self.thread and self.thread.is_alive()
