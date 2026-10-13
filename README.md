# monitor_system_mcp

## 项目简介

`monitor_system_mcp` 是一个基于 **MCP（Model Context Protocol）** 的监控代理服务器。它作为 AI 助手（如 Claude）与 [monitor_system_ai](https://github.com/zsl-007/monitor_system_ai) 监控系统之间的桥梁，将监控系统的运维 API 封装为 MCP Tool，使 AI 模型能够通过自然语言直接查询多台服务器的健康状态、资源使用、组件状态、SSL 证书、报警历史等信息。

**解决的核心问题：** 运维人员无需登录多个监控系统面板，只需通过 AI 对话即可快速了解整个服务器集群的运行状况，实现"对话式运维"。

## 功能特性

- **多服务器管理**：通过 `servers.json` 配置文件统一管理多台被监控服务器，支持按环境（production / test / development）和角色（web / database / cache）筛选
- **15 个 MCP Tool**：覆盖服务器健康、资源状态、组件监控、SSL 证书、API 监控、报警、历史趋势等完整运维场景
- **批量查询**：支持 `fleet_overview`（集群总览）和 `batch_server_status`（批量状态查询）等多服务器聚合查询
- **安全认证**：通过 `X-Ops-Token` 请求头向监控系统进行身份验证，Token 不会通过 MCP Tool 暴露给 AI 模型
- **streamable-http 传输**：基于 MCP 协议的 streamable-http 传输模式，支持远程调用
- **systemd 服务化部署**：提供 systemd service 配置，支持开机自启和故障自动重启
- **环境变量配置**：主机、端口、配置文件路径均可通过环境变量覆盖

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3 |
| MCP 框架 | `mcp`（Model Context Protocol SDK） |
| HTTP 客户端 | `httpx` |
| 传输协议 | streamable-http |
| 进程管理 | systemd |
| 配置格式 | JSON |

## 项目结构

```
monitor_system_mcp/
├── server.py                        # 主程序：MCP Server 定义、15 个 Tool、启动入口
├── servers.json                     # 服务器配置文件（被监控服务器列表）
├── start_python3.sh                 # 启动脚本（激活虚拟环境并运行 server.py）
└── monitor-system-mcp.service       # systemd 服务配置文件
```

### 文件说明

| 文件 | 说明 |
|------|------|
| `server.py` | 项目唯一的核心代码文件，包含 `ServerRegistry`（服务器注册表）、`MonitorSystemClient`（监控 API 客户端）和 15 个 MCP Tool 定义，约 794 行 |
| `servers.json` | 声明被监控的服务器列表，每台服务器包含 id、name、environment、role、os、description、monitor_system_url、monitor_system_token |
| `start_python3.sh` | Bash 启动脚本，切换到项目目录、激活 Python 虚拟环境、执行 `python3 server.py` |
| `monitor-system-mcp.service` | systemd Unit 文件，配置服务以 root 用户运行、异常 10 秒后自动重启 |

## 安装与部署

### 前置条件

1. Python 3.8+ 运行环境
2. 已部署 [monitor_system_ai](https://github.com/zsl-007/monitor_system_ai) 监控系统并获取了访问 Token
3. 已安装 `mcp` 和 `httpx` Python 包

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/zsl-007/monitor_system_mcp.git
cd monitor_system_mcp

# 2. 创建并激活 Python 虚拟环境
python3 -m venv MonitorSystemEnv
source MonitorSystemEnv/bin/activate

# 3. 安装依赖
pip install mcp httpx

# 4. 编辑服务器配置
vim servers.json
```

### 配置 servers.json

在 `servers.json` 中添加被监控的服务器：

```json
{
  "servers": [
    {
      "id": "prod-web-01",
      "name": "Web服务器-01",
      "environment": "production",
      "role": "web",
      "os": "Ubuntu 24.04",
      "description": "生产环境 Web 服务器",
      "monitor_system_url": "http://192.168.0.98:18770",
      "monitor_system_token": "your-token-here"
    },
    {
      "id": "prod-db-01",
      "name": "数据库服务器-01",
      "environment": "production",
      "role": "database",
      "os": "Ubuntu 24.04",
      "description": "生产环境数据库服务器",
      "monitor_system_url": "http://192.168.0.236:18771",
      "monitor_system_token": "your-token-here"
    }
  ]
}
```

**字段说明：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 服务器唯一标识，用于所有 Tool 的 `server_id` 参数 |
| `name` | 否 | 服务器显示名称 |
| `environment` | 否 | 环境标签，如 `production`、`test`、`development` |
| `role` | 否 | 服务器角色，如 `web`、`database`、`cache` |
| `os` | 否 | 操作系统信息 |
| `description` | 否 | 服务器描述 |
| `monitor_system_url` | 是 | monitor_system_ai 监控系统的 API 地址 |
| `monitor_system_token` | 是 | 监控系统的访问 Token（通过 `X-Ops-Token` 请求头传递） |

### systemd 服务部署

```bash
# 1. 将项目部署到 /home/monitor_system_mcp
cp -r monitor_system_mcp /home/monitor_system_mcp

# 2. 根据实际路径修改 start_python3.sh 中的虚拟环境路径
vim /home/monitor_system_mcp/start_python3.sh

# 3. 安装 systemd 服务
cp /home/monitor_system_mcp/monitor-system-mcp.service /etc/systemd/system/

# 4. 启动并设置开机自启
systemctl daemon-reload
systemctl enable monitor-system-mcp
systemctl start monitor-system-mcp

# 5. 查看运行状态
systemctl status monitor-system-mcp
```

## 使用说明

### 直接运行

```bash
python3 server.py
```

启动后，MCP Server 将监听 `http://127.0.0.1:19000`，提供 streamable-http 传输接口。

### 连接到 AI 助手

在支持 MCP 的 AI 客户端（如 Claude Desktop）中配置 MCP Server：

```json
{
  "mcpServers": {
    "system-monitor": {
      "url": "http://127.0.0.1:19000"
    }
  }
}
```

连接成功后，AI 助手即可调用以下 15 个 Tool 进行运维查询。

### 环境变量配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `MONITOR_SYSTEM_MCP_HOST` | `127.0.0.1` | MCP Server 监听地址 |
| `MONITOR_SYSTEM_MCP_PORT` | `19000` | MCP Server 监听端口 |
| `MONITOR_SYSTEM_SERVERS_CONFIG` | `servers.json`（同目录下） | 服务器配置文件路径 |

示例：

```bash
export MONITOR_SYSTEM_MCP_HOST=0.0.0.0
export MONITOR_SYSTEM_MCP_PORT=8080
python3 server.py
```

## MCP Tool 说明

本项目共定义 **15 个 MCP Tool**，分为三类：服务器管理类（Tool 1-2）、单服务器监控类（Tool 3-13）、多服务器聚合类（Tool 14-15）。

### 服务器管理

#### 1. `list_servers` — 获取服务器列表

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `environment` | `str` | 否 | 按环境筛选，如 `production` |
| `role` | `str` | 否 | 按角色筛选，如 `web` |

返回所有已配置服务器的基本信息（不包含 Token）。

#### 2. `server_info` — 获取服务器详情

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |

返回指定服务器的详细配置信息（不包含 Token）。

### 单服务器监控

#### 3. `server_overview` — 服务器整体健康状态

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |

调用后端 `GET /api/ops/overview`，返回服务器整体健康概览。

#### 4. `server_status` — 服务器当前资源状态

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |

调用后端 `GET /api/ops/status`，返回当前 CPU、内存、磁盘和网络使用状态。

#### 5. `list_components` — 所有组件状态

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |

调用后端 `GET /api/ops/components`，返回服务器上所有组件（如 Redis、RabbitMQ 等）的运行状态。

#### 6. `component_status` — 指定组件状态

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |
| `name` | `str` | 是 | 组件名称，如 `redis`、`rabbitmq` |

调用后端 `GET /api/ops/components/{name}`，返回指定组件的详细状态。

#### 7. `ssl_certificates` — SSL 证书状态

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |
| `days` | `int` | 否 | 查询未来多少天内即将过期的证书，默认 30 |

调用后端 `GET /api/ops/ssl?days={days}`，返回 SSL 证书状态及即将过期的证书列表。

#### 8. `api_status` — API 监控状态

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |

调用后端 `GET /api/ops/apis`，返回被监控 API 的健康状态。

#### 9. `alerts` — 最近报警数据

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |
| `limit` | `int` | 否 | 返回报警条数上限，默认 20 |

调用后端 `GET /api/ops/alerts?limit={limit}`，返回最近的报警记录。

#### 10. `monitor_history` — 历史监控数据

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |

调用后端 `GET /api/ops/history`，返回历史监控数据。

#### 11. `metric_trend` — 监控指标趋势

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |
| `metric` | `str` | 是 | 指标名称，如 `cpu`、`memory`、`disk`、`network` |
| `hours` | `int` | 否 | 查询最近多少小时的数据，默认 24 |
| `interval` | `str` | 否 | 聚合间隔，如 `1h`，默认 `1h` |

调用后端 `GET /api/ops/trend?metric={metric}&hours={hours}&interval={interval}`，返回指定指标的趋势数据。

#### 12. `monitor_configs` — 监控配置

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |

调用后端 `GET /api/ops/configs`，返回当前监控配置信息。

#### 13. `scheduler_status` — APScheduler 状态

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_id` | `str` | 是 | 服务器 ID |

调用后端 `GET /api/ops/scheduler`，返回后端 APScheduler 定时任务调度器的运行状态。

### 多服务器聚合

#### 14. `fleet_overview` — 集群总览

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `environment` | `str` | 否 | 按环境筛选，如 `production` |
| `role` | `str` | 否 | 按角色筛选，如 `web`、`database` |

遍历所有（或筛选后的）服务器，逐一调用 `GET /api/ops/overview`，返回每台服务器的健康概览。适合回答"所有服务器有没有问题？""生产服务器现在怎么样？"等问题。

#### 15. `batch_server_status` — 批量服务器状态

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_ids` | `List[str]` | 是 | 服务器 ID 数组，如 `["prod-web-01", "prod-db-01"]` |

遍历指定的服务器列表，逐一调用 `GET /api/ops/status`，返回每台服务器当前的 CPU、内存、磁盘和网络状态。

## 架构说明

### 整体架构

```
+--------------+     MCP (streamable-http)     +---------------------+     HTTP (X-Ops-Token)     +----------------------+
|   AI 助手     | <---------------------------> |  monitor_system_mcp  | <-----------------------> |  monitor_system_ai   |
| (Claude 等)  |         15 个 Tool            |   (本项目, :19000)   |       /api/ops/*          |  (监控系统, :18770)   |
+--------------+                               +---------------------+                            +----------------------+
                                                       |
                                                       | 读取
                                                       v
                                               +---------------+
                                               |  servers.json  |
                                               | (服务器配置表)  |
                                               +---------------+
```

### 核心模块

#### 1. ServerRegistry（服务器注册表）

- **职责**：加载并管理 `servers.json` 中的多服务器配置
- **初始化时**：读取配置文件，校验每台服务器必须有 `id`、`monitor_system_url`、`monitor_system_token`，检测 ID 是否重复
- **提供方法**：
  - `get(server_id)` — 按 ID 获取单台服务器配置
  - `all()` — 获取所有服务器配置列表
- **设计特点**：不使用数据库（如 SQLite），纯 JSON 文件配置，轻量高效

#### 2. MonitorSystemClient（监控 API 客户端）

- **职责**：封装对 monitor_system_ai 后端 API 的 HTTP 调用
- **认证方式**：通过 `X-Ops-Token` 请求头传递访问 Token
- **请求方式**：使用 `httpx.get()` 发起 HTTP GET 请求，超时时间 15 秒
- **错误处理**：捕获 `HTTPStatusError` 和其他异常，统一返回 `{"success": False, "error": ...}` 格式

#### 3. MCP Tool 层（15 个 Tool）

- **职责**：将后端 API 封装为 MCP Tool，供 AI 助手调用
- **设计模式**：每个 Tool 通过 `@mcp.tool()` 装饰器注册，内部调用 `MonitorSystemClient.get()` 访问后端
- **安全设计**：`list_servers` 和 `server_info` 两个 Tool 明确不返回 `monitor_system_token`，避免 Token 泄露给 AI 模型

### 数据流

```
AI 助手发起查询
    |
    v
MCP Tool 被调用（如 server_status("prod-web-01")）
    |
    v
ServerRegistry.get("prod-web-01")  ->  获取服务器配置（url + token）
    |
    v
MonitorSystemClient.get("/api/ops/status")
    |
    v
httpx.get("http://192.168.0.98:18770/api/ops/status", headers={"X-Ops-Token": "xxx"})
    |
    v
monitor_system_ai 返回 JSON 数据
    |
    v
MCP Tool 返回结果给 AI 助手
```

### 后端 API 端点汇总

本项目通过 `MonitorSystemClient` 调用以下后端 API 端点：

| 端点 | 对应 Tool | 说明 |
|------|-----------|------|
| `GET /api/ops/overview` | `server_overview`, `fleet_overview` | 整体健康概览 |
| `GET /api/ops/status` | `server_status`, `batch_server_status` | 当前资源状态 |
| `GET /api/ops/components` | `list_components` | 所有组件状态 |
| `GET /api/ops/components/{name}` | `component_status` | 指定组件状态 |
| `GET /api/ops/ssl?days=N` | `ssl_certificates` | SSL 证书状态 |
| `GET /api/ops/apis` | `api_status` | API 监控状态 |
| `GET /api/ops/alerts?limit=N` | `alerts` | 报警数据 |
| `GET /api/ops/history` | `monitor_history` | 历史监控数据 |
| `GET /api/ops/trend?metric=X&hours=N&interval=Y` | `metric_trend` | 指标趋势 |
| `GET /api/ops/configs` | `monitor_configs` | 监控配置 |
| `GET /api/ops/scheduler` | `scheduler_status` | APScheduler 状态 |
