# Network_Impairment_Engine Module

The `engine` module is an edge execution component of the system. It executes traffic emulation and network control operations according to commands issued by the control center. Its design goal is to enable controllable injection and dynamic adjustment of network behaviors in a simulated environment, so as to evaluate the system’s responses under different load conditions and abnormal scenarios.

## Core Functions

### 1. Receiving control commands

The `engine` module listens for messages from the control side and performs corresponding actions based on the received command type:

- **Bandwidth control**: configures the transmit and receive rates of network interfaces using the `tc` tool.
- **Traffic generation**:
  - supports specifying the destination IP address and port;
  - supports continuous traffic transmission or sending a fixed number of UDP packets with a given packet size.
- **Stop traffic generation**:
  - supports stopping traffic toward a specific destination;
  - supports stopping all ongoing traffic generation tasks.

### 2. Traffic generation module

- Uses the UDP protocol to send packets to specified destinations.
- Supports configuring packet size, sending rate, and the total number of packets.
- Can be used together with tools such as **`ifstat`** inside Docker containers for visualization and debugging.

```bash
apt update && apt install -y ifstat
```

## Installation
### 1. Copy the engine directory

Copy the `engine` directory to the root of `docker_open5gs`:
```bash
cp -r engine /path/to/docker_open5gs/

```


The directory structure should look like:
```yaml
docker_open5gs/
├── engine/
│   ├── __init__.py
│   ├── load_control_agent.py
│   └── ...
├── docker-compose.yaml
└── ...
```
2. Modify the docker-compose.yaml file

In docker-compose.yaml, update the configuration of each core network function container that needs to run the engine (e.g., amf, smf, nssf).

✅ Add volume mount

```
volumes:
  - ./engine:/opt/engine
```



✅ Set the startup command
```
command: bash -c "cd /opt && python3 -m engine.load_control_agent & cd /open5gs && bash ../open5gs_init.sh && wait"
```


✅ Expose the control port


```
expose:
  - "7799/tcp"
```

✅ Add network control capability

```
cap_add:
  - NET_ADMIN
```

Example configuration
```
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

Then restart the system with:

docker compose -f docker-compose.yaml up