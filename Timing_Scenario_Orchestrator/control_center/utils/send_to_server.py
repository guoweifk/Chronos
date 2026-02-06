import json
import logging
import socket

AGENT_PORT = 22222  # 自己的端口

def send_to_server(agent_ip: str, message_obj):
    """
    发送消息到 engine，并尝试读取对方返回的 JSON 结果。

    返回:
        (success, response)
        - success: True/False
        - response:
            - 成功且对方有返回：解析后的 JSON 对象 或 原始字符串
            - 成功但无返回：None
            - 失败：None
    """
    try:
        # 将 dataclass / 对象转为 JSON 字符串
        json_data = json.dumps(message_obj, default=lambda o: o.__dict__)
        logging.debug(f"[→] 发送至 {agent_ip}:{AGENT_PORT}，内容: {json_data}")

        with socket.create_connection((agent_ip, AGENT_PORT), timeout=3) as sock:
            # 先发送
            sock.sendall(json_data.encode("utf-8"))

            # 告诉对面“我发完了”，有些 server 需要这个才能开始回数据
            try:
                sock.shutdown(socket.SHUT_WR)
            except OSError:
                # 某些平台/场景可能不需要/不支持，忽略即可
                pass

            # 再接收对方返回
            chunks = []
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                chunks.append(data)

        if not chunks:
            logging.info(f"[✓] 成功发送消息到 engine {agent_ip}，但对方未返回数据")
            return True, None

        raw_resp = b"".join(chunks).decode("utf-8", errors="replace")
        logging.debug(f"[←] 从 engine {agent_ip} 收到响应: {raw_resp}")

        # 尝试按 JSON 解析
        try:
            resp_obj = json.loads(raw_resp)
            return True, resp_obj
        except json.JSONDecodeError:
            # 如果不是合法 JSON，就原样返回字符串
            return True, raw_resp

    except Exception as e:
        logging.error(f"[×] 发送消息到 engine {agent_ip} 失败: {e}")
        return False, None
