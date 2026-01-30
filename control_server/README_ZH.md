# Server 模块说明

`server` 模块是整个系统的控制中心，负责接收`Center`控制命令，并将指令分发给各个部署在网元容器中的 `agent` 组件。

---

## 核心功能

### 控制指令分发

- 接收来自`Center`的控制消息（如 HTTP 请求或其他格式）
- 根据指令类型构造消息，并将其发送给对应网元内的 `agent`
- 支持以下控制动作：
  - **带宽控制**：通过 `tc` 限制目标`agent`带宽
  - **发送流量**：指示`agent` 向指定目标发送 UDP 流量
  - **停止发送**：中止`agent`目标的流量任务
  - **停止所有**：清除`agent`当前所有活跃任务
  - **发送流量**：指示当前`server`宿主机向指定目标发送 UDP 流量
  - **停止发送**：中止当前`server`宿主机目标的流量任务
  - **停止所有**：清除当前`server`宿主机当前所有活跃任务

### 2. 多目标管理

- 可同时控制多个网元的 `agent`
- 支持批量广播、单个网元指令定向发送

### 3. 日志管理
日志在control_server的utils目录下

## 安装教程

### 1. 复制 control_server 目录

将本 `control_server` 文件夹复制到 `docker_open5gs` 根目录下：

```bash
cp -r agent /path/to/docker_open5gs/
```
目录结构类似：
```yaml
docker_open5gs/
├── control_server/
│   ├── __init__.py
│   ├── load_control_manager.py
│   └── ...
├── docker-compose.yaml
└── ...
```

### 2. 复制 start.sh 到 docker_open5gs下，执行

