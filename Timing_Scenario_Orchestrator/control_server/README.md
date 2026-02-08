Server Module
=============

The `server` module serves as the control hub of the system. It receives control commands from the `Center` and dispatches them to the `agent` components deployed inside individual network function containers.

---

Core Functions
--------------

### Control command dispatching

- Receives control messages from the `Center` (e.g., HTTP requests or other formats).
- Constructs control messages according to the command type and sends them to the corresponding `agent` running inside each network function container.
- Supports the following control actions:

  - **Bandwidth control**: limits the bandwidth of the target `agent` using `tc`.
  - **Traffic generation**: instructs a target `agent` to send UDP traffic to a specified destination.
  - **Stop traffic generation**: stops traffic tasks for a specified destination on the target `agent`.
  - **Stop all tasks**: terminates all active traffic tasks on the target `agent`.
  - **Traffic generation (local)**: instructs the host machine running the `server` to send UDP traffic to a specified destination.
  - **Stop traffic generation (local)**: stops traffic tasks for a specified destination on the `server` host.
  - **Stop all tasks (local)**: terminates all active traffic tasks on the `server` host.

### 2. Multi-target management

- Supports simultaneous control of multiple `agent` instances deployed on different network functions.
- Supports broadcast commands and targeted commands to individual network functions.

### 3. Log management

Log files are stored in the `utils` directory under `control_server`.

---

Installation
------------

### 1. Copy the control_server directory

Copy the `control_server` directory to the root of `docker_open5gs`:

```bash
cp -r control_server /path/to/docker_open5gs/
```
The directory structure should look like:
```yaml
docker_open5gs/
├── control_server/
│   ├── __init__.py
│   ├── load_control_manager.py
│   └── ...
├── docker-compose.yaml
└── ...
```

### 2. Copy start.sh to docker_open5gs and execute

Copy start.sh to the docker_open5gs directory and execute it to start the server.