# Network_Impairment_Engine 模块说明

`engine` 模块是系统的边缘执行组件，负责根据控制中心下发的指令，执行流量模拟和网络控制操作。其设计目标是在模拟环境中对网络行为进行可控注入与动态调整，便于测试系统在不同负载或异常条件下的响应能力。

## 核心功能

### 1. 接收控制信息

`engine` 模块监听来自控制端的消息，根据消息类型执行对应操作：

- **带宽控制**：使用 `tc` 工具配置网络接口的发送/接收速率等参数。
- **发送流量**：
  - 可指定目标 IP 和端口。
  - 支持持续发送或仅发送指定次数的特定大小 UDP 流量。
- **停止发送**：
  - 支持停止指定目标的流量发送。
  - 支持一键停止所有目标流量任务。

### 2. 发送流量模块

- 使用 UDP 协议向指定目标发送数据包。
- 支持设定包大小、发送速率和总发送次数。
- 可搭配 **`ifstat` ** 等工具在docker中进行效果可视化或调试分析。

```bash
apt update && apt install -y ifstat
```
## 安装教程

### 1. 复制 Engine 目录

将本 `engine` 文件夹复制到 `docker_open5gs` 根目录下：

```bash
cp -r engine /path/to/docker_open5gs/
```
目录结构类似：
```yaml
docker_open5gs/
├── engine/
│   ├── __init__.py
│   ├── load_control_agent.py
│   └── ...
├── docker-compose.yaml
└── ...
```
### 2. 修改 docker-compose.yaml 文件
在docker-compose.yaml 文件中，修改每个需要运行 engine 的核心网网元容器（如 amf、smf、nssf 等）对应配置：

✅ 增加挂载目录
```yaml
volumes:
  - ./engine:/opt/engine
```
✅ 设置启动命令
```yaml
command: bash -c "cd /opt && python3 -m engine.load_control_agent & cd /open5gs && bash ../open5gs_init.sh && wait"
```

✅ 暴露控制端口
```yaml
expose:
  - "7799/tcp"
```

✅ 添加网络控制权限
```yaml
cap_add:
  - NET_ADMIN
```

示例内容
```yaml
nssf:
  image: docker_open5gs
  depends_on:
    - nrf
    - scp
    - mongo
  container_name: nssf
  env_file:
    - .env
  environment:
    - COMPONENT_NAME=nssf
  volumes:
    - ./nssf:/mnt/nssf
    - ./log:/open5gs/install/var/log/open5gs
    - /etc/timezone:/etc/timezone:ro
    - /etc/localtime:/etc/localtime:ro
    - ./engine:/opt/engine
  command: bash -c "cd /opt && python3 -m engine.load_control_agent & cd /open5gs && bash ../open5gs_init.sh && wait"
  expose:
    - "7777/tcp"
    - "7799/tcp"
  cap_add:
    - NET_ADMIN
  networks:
    default:
      ipv4_address: ${NSSF_IP}

```

然后重新docker compose -f docker-compose.yaml up 即可
