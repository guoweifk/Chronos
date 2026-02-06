# s1ap_handler.py
import socket
import time
import threading
from threading import Lock
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import logging
import logging.handlers

from pycrate_asn1dir import S1AP  
from eNB_LOCAL import *           
from myutils import hexdump      

class MultiThreadedS1APHandler:
    """
    高性能版 S1AP 消息处理器：
    - 固定 N 个 worker 循环从队列取消息处理（不再每消息 submit 任务）
    - 接收线程只负责入队；队列有限制，支持丢弃计数（背压）
    - 事件日志写入使用独立单线程 I/O 执行器，避免与主计算互相挤压
    - 统计信息增强 + 持久化到 stats.txt
    """
    def __init__(
        self,
        client_socket,
        ue_dict,
        registered_ue_dict,
        registered_queue,
        ims_pdn_ue_dict,
        ims_pdn_queue,
        max_workers=64,
        queue_capacity=20000,          # 建议 5k~50k 之间，根据场景调
        recv_bufsize=32768,            # 每次 recv 的缓冲
        socket_rcvbuf_bytes=2*1024*1024
    ):
        self.client = client_socket
        self.ue_dict = ue_dict  # {enb_ue_id: [UE对象, ...]} 仍用于查 UE
        # 下面两个不再使用，但保留参数兼容主程序
        self.registered_ue_dict = registered_ue_dict
        self.ims_pdn_ue_dict = ims_pdn_ue_dict

        # 业务队列（保持与主程序对接）
        self.registered_queue = registered_queue
        self.ims_pdn_queue = ims_pdn_queue

        # 主控
        self.running = True
        self.max_workers = max_workers

        self.message_queue = Queue(maxsize=queue_capacity)

        self.stats = {
            'received': 0,
            'processed': 0,
            'errors': 0,
            'queue_full': 0,  
            'dropped': 0        
        }
        self.stats_lock = Lock()

        self.active_workers = 0
        self.thread_count_lock = Lock()
        self.peak_workers = 0

        self.perf_data = defaultdict(list)
        self.perf_lock = Lock()

        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="S1AP-Worker"
        )

        self.io_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="S1AP-IO"
        )

        self._init_logging()

        self.recv_bufsize = recv_bufsize
        self.receiver_thread = threading.Thread(target=self._receiver_loop, name="S1AP-Receiver", daemon=True)
        self.stats_thread = threading.Thread(target=self._stats_loop, name="S1AP-Stats", daemon=True)

        self._start_workers(max_workers)
        try:
            self.client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, socket_rcvbuf_bytes)
            self.client.settimeout(0.1)
        except Exception as e:
            logging.getLogger("s1ap").warning(f"设置 socket 失败: {e}")

        # 启动
        self.receiver_thread.start()
        self.stats_thread.start()

        logging.getLogger("s1ap").info(
            f"多线程处理器启动 | workers={max_workers}, queue_capacity={queue_capacity}, recv_bufsize={recv_bufsize}"
        )


    def _init_logging(self):
        """
        轻量日志：避免在热路径大量 print。
        这里仅配置一个基础 logger（控制台可选）。统计数据另写 stats.txt。
        """
        self.logger = logging.getLogger("s1ap")
        self.logger.setLevel(logging.INFO)

        # 控制台输出（可按需关闭）
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
            ch.setFormatter(fmt)
            self.logger.addHandler(ch)


    def _receiver_loop(self):
        logger = self.logger
        logger.info("接收线程已启动")
        while self.running:
            try:
                buffer = self.client.recv(self.recv_bufsize)
                if not buffer:
                    continue
                with self.stats_lock:
                    self.stats['received'] += 1
                # 尝试快速入队；满了就统计并丢弃（或改为阻塞 put）
                try:
                    self.message_queue.put_nowait(buffer)
                except:
                    with self.stats_lock:
                        self.stats['queue_full'] += 1
                        self.stats['dropped'] += 1
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.warning(f"接收异常: {e}")
                    time.sleep(0.01)
        logger.info("接收线程退出")

    def _start_workers(self, num_workers: int):
        for _ in range(num_workers):
            self.executor.submit(self._worker_loop)

    def _worker_loop(self):
        # 统一的 worker：循环从队列获取数据并处理
        with self.thread_count_lock:
            self.active_workers += 1
            if self.active_workers > self.peak_workers:
                self.peak_workers = self.active_workers

        try:
            while self.running:
                try:
                    buffer = self.message_queue.get(timeout=0.1)
                except Empty:
                    continue

                total_start = time.time()
                try:
                    # 解析/判别
                    parse_start = time.time()
                    enb_ue_id, is_registered, is_establish_ims_pdn, is_disconnect_ims_pdn = \
                        self.extract_enb_ue_s1ap_id(buffer)
                    self._record_perf('message_parse', time.time() - parse_start)

                    if enb_ue_id is None:
                        # 丢弃未知消息
                        continue

                    # 查 UE
                    lookup_start = time.time()
                    ue_entry = self.ue_dict.get(enb_ue_id)
                    ue = ue_entry[0] if ue_entry else None
                    self._record_perf('ue_lookup', time.time() - lookup_start)

                    if ue:
                        # 处理 S1AP
                        process_start = time.time()
                        self._process_message_for_ue(buffer, ue)
                        self._record_perf('process_s1ap', time.time() - process_start)

                        # 状态更新与后续队列
                        status_start = time.time()
                        if is_registered:
                            self._handle_registration_async(enb_ue_id, ue)
                        if is_establish_ims_pdn:
                            self._handle_ims_pdn_async(enb_ue_id, ue)
                        if is_disconnect_ims_pdn:
                            self._handle_disconnect_async(ue)
                        self._record_perf('status_update', time.time() - status_start)
                    else:
                        # 不再 print，避免热路径阻塞
                        pass

                    self._record_perf('total_processing', time.time() - total_start)

                    with self.stats_lock:
                        self.stats['processed'] += 1

                except Exception as e:
                    with self.stats_lock:
                        self.stats['errors'] += 1
                finally:
                    self.message_queue.task_done()
        finally:
            with self.thread_count_lock:
                self.active_workers -= 1


    def _record_perf(self, metric_name, duration):
        with self.perf_lock:
            lst = self.perf_data[metric_name]
            lst.append(duration)
            # 截断，避免无限增长
            if len(lst) > 2000:
                self.perf_data[metric_name] = lst[-1000:]

    def _get_perf_summary(self):
        summary = {}
        with self.perf_lock:
            for metric, data in self.perf_data.items():
                if data:
                    summary[metric] = {
                        'avg': sum(data) / len(data),
                        'max': max(data),
                        'count': len(data)
                    }
        return summary


    def _handle_registration_async(self, enb_ue_id, ue):
        # 落盘到 register_success.txt + 入业务队列
        self.io_executor.submit(self._write_line_safe, "register_success.txt", f"{ue.imsi}注册成功\n")
        # 直接入队
        try:
            self.registered_queue.put_nowait(ue)
        except:
            # 如果你希望不丢，可以改成阻塞 put + 超时
            self.registered_queue.put(ue, timeout=0.5)

    def _handle_ims_pdn_async(self, enb_ue_id, ue):
        self.io_executor.submit(self._write_line_safe, "pdn_success.txt", f"{ue.imsi}IMS_PDN建立成功\n")
        try:
            self.ims_pdn_queue.put_nowait(ue)
        except:
            self.ims_pdn_queue.put(ue, timeout=0.5)

    def _handle_disconnect_async(self, ue):
        self.io_executor.submit(self._write_line_safe, "rebuild_ims_pdn.txt", f"{ue.imsi}重建ims_pdn会话\n")
        # 将UE放回注册队列重建
        try:
            self.registered_queue.put_nowait(ue)
        except:
            self.registered_queue.put(ue, timeout=0.5)


    @staticmethod
    def _write_line_safe(filepath: str, line: str):
        try:
            with open(filepath, "a", buffering=1) as f:
                f.write(line)
        except Exception as e:
            # 只在 I/O 线程打印一次，不干扰热路径
            logging.getLogger("s1ap").warning(f"写入 {filepath} 失败: {e}")


    def _process_message_for_ue(self, buffer, ue):
        try:
            session_dict = ue.session_dict
            client_number = session_dict.get('MME-IN-USE', 1)
            PDU = ue.PDU
            new_PDU, new_client, new_session_dict = ProcessS1AP(
                PDU,
                self.client,
                session_dict,
                client_number,
                buffer=buffer
            )
            ue.PDU = new_PDU
            ue.session_dict = new_session_dict
        except Exception as e:
            # 避免热路径 print
            with self.stats_lock:
                self.stats['errors'] += 1


    def _stats_loop(self):
        last_received = 0
        last_processed = 0
        while self.running:
            time.sleep(5)
            with self.stats_lock:
                current_received = self.stats['received']
                current_processed = self.stats['processed']
                queue_size = self.message_queue.qsize()
                recv_rate = (current_received - last_received) / 5.0
                proc_rate = (current_processed - last_processed) / 5.0
                queue_full = self.stats['queue_full']
                errors = self.stats['errors']
                dropped = self.stats['dropped']

            with self.thread_count_lock:
                cur_active = self.active_workers
                peak = self.peak_workers

            perf = self._get_perf_summary()

            # 组装统计行
            msg = (
                f"[S1AP Stats] 接收: {recv_rate:.1f}/s, 处理: {proc_rate:.1f}/s, "
                f"队列: {queue_size}, 错误: {errors}, 队列满: {queue_full}, 丢弃: {dropped}, "
                f"活跃worker: {cur_active}/{self.max_workers}, 峰值: {peak}"
            )
            if 'total_processing' in perf:
                avg_ms = perf['total_processing']['avg'] * 1000
                max_ms = perf['total_processing']['max'] * 1000
                msg += f", 平均处理时间: {avg_ms:.2f}ms, 最大处理时间: {max_ms:.2f}ms"

            # 写入 stats.txt
            try:
                with open("stats.txt", "a") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
                    if perf:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [详细性能] ")
                        for metric, data in perf.items():
                            f.write(f"{metric}: {data['avg']*1000:.2f}ms(avg), ")
                        f.write("\n")
            except Exception as e:
                logging.getLogger("s1ap").warning(f"写入 stats.txt 失败: {e}")

            with self.stats_lock:
                last_received = current_received
                last_processed = current_processed


    def get_stats(self):
        with self.stats_lock:
            stats = self.stats.copy()
        with self.thread_count_lock:
            stats['active_workers'] = self.active_workers
            stats['peak_workers'] = self.peak_workers
            stats['thread_utilization'] = (self.active_workers / self.max_workers) * 100.0
        stats['queue_size'] = self.message_queue.qsize()
        stats['perf_summary'] = self._get_perf_summary()
        return stats

    def stop(self):
        self.logger.info("正在停止处理器...")
        self.running = False

        if self.receiver_thread and self.receiver_thread.is_alive():
            self.receiver_thread.join(timeout=3)
        if self.stats_thread and self.stats_thread.is_alive():
            self.stats_thread.join(timeout=1)

        # 等待消息队列清空（可选）
        # self.message_queue.join()

        # 优雅关闭执行器
        self.executor.shutdown(wait=True, timeout=10)
        self.io_executor.shutdown(wait=True, timeout=5)

        final_stats = self.get_stats()
        self.logger.info(f"最终统计: {final_stats}")
        self.logger.info("处理器已停止")

    @staticmethod
    def extract_enb_ue_s1ap_id(buffer):
        try:
            # 1. 提取 eNB-UE-S1AP-ID
            enb_ue_id = None
            patterns = [
                (b'\x00\x08\x00\x02', 4),
                (b'\x00\x08\x00\x03\x40', 5)
            ]
            for pattern, offset in patterns:
                idx = buffer.find(pattern)
                if idx != -1 and len(buffer) >= idx + offset + 2:
                    enb_ue_id = int.from_bytes(buffer[idx + offset:idx + offset + 2], byteorder='big')
                    break

            # 2. 判断消息类型
            is_registered = False
            is_establish_ims_pdn = False
            is_disconnect_ims_pdn = False

            if buffer.startswith(b'\x00\x09'):  # DownlinkNASTransport
                # if len(buffer) > 34:
                #     if (buffer[32] == 0x07 and buffer[33] == 0x61) or \
                #     (buffer[31] == 0x07 and buffer[32] == 0x61) or \
                #     (buffer[30] == 0x07 and buffer[31] == 0x61) :
                #         is_registered = True
                # time.sleep(0.5) # 因为千通的网还需要连续收到两个数据包，才算真正注册成功。
                is_registered = True

            elif buffer.startswith(b'\x00\x05'):  # E-RABSetupRequest
                # time.sleep(2)  # 收到PDN建立报之后，eNB和UE需要返回两个响应包。需要至少0.2s的时间
                # 不能在这里sleep，要不然收到消息之后在处理前sleep了。阻塞了。无效等待
                # 因此需要再workflow里等待。处理PDN建立
                is_establish_ims_pdn = True

            elif buffer.startswith(b'\x00\x07'):  # E-RABReleaseCommand
                is_disconnect_ims_pdn = True

            return enb_ue_id, is_registered, is_establish_ims_pdn, is_disconnect_ims_pdn

        except Exception:
            return None, False, False, False
                    