import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from mcp.server import MCPServer


# ============================================================
# 配置
# ============================================================

MCP_HOST = os.getenv(
    "MONITOR_SYSTEM_MCP_HOST",
    "127.0.0.1"
)

MCP_PORT = int(
    os.getenv(
        "MONITOR_SYSTEM_MCP_PORT",
        "19000"
    )
)

CONFIG_FILE = Path(
    os.getenv(
        "MONITOR_SYSTEM_SERVERS_CONFIG",
        Path(__file__).with_name("servers.json")
    )
)

# ============================================================
# MCP Server
# ============================================================

mcp = MCPServer("system-monitor")


# ============================================================
# Server Registry
# ============================================================

class ServerRegistry:
    """
    多服务器配置管理。

    配置来源：
        servers.json

    不使用 SQLite。
    """

    def __init__(self, config_file: Path):
        self.config_file = Path(config_file)
        self.servers: Dict[str, Dict[str, Any]] = {}

        self.load()

    def load(self):
        """加载服务器配置"""

        if not self.config_file.exists():
            raise FileNotFoundError(
                f"服务器配置文件不存在: {self.config_file}"
            )

        with self.config_file.open(
            "r",
            encoding="utf-8"
        ) as f:
            config = json.load(f)

        server_list = config.get(
            "servers",
            []
        )

        if not isinstance(server_list, list):
            raise ValueError(
                "servers.json 中的 servers 必须是数组"
            )

        self.servers.clear()

        for server in server_list:

            server_id = server.get("id")

            if not server_id:
                raise ValueError(
                    "服务器配置缺少 id"
                )

            if server_id in self.servers:
                raise ValueError(
                    f"服务器 ID 重复: {server_id}"
                )

            if not server.get(
                "monitor_system_url"
            ):
                raise ValueError(
                    f"服务器 {server_id} "
                    f"缺少 monitor_system_url"
                )

            if not server.get(
                "monitor_system_token"
            ):
                raise ValueError(
                    f"服务器 {server_id} "
                    f"缺少 monitor_system_token"
                )

            self.servers[
                server_id
            ] = server

        print(
            f"已加载 {len(self.servers)} 台服务器"
        )

    def get(
        self,
        server_id: str
    ) -> Dict[str, Any]:

        server = self.servers.get(
            server_id
        )

        if not server:
            raise ValueError(
                f"服务器不存在: {server_id}"
            )

        return server

    def all(self):
        return list(
            self.servers.values()
        )


registry = ServerRegistry(
    CONFIG_FILE
)


# ============================================================
# Monitor System Client
# ============================================================

class MonitorSystemClient:

    def __init__(
        self,
        server: Dict[str, Any]
    ):

        self.server = server

        self.base_url = (
            server[
                "monitor_system_url"
            ].rstrip("/")
        )

        self.token = (
            server[
                "monitor_system_token"
            ]
        )

    def get(
        self,
        path: str,
        params: Optional[
            Dict[str, Any]
        ] = None
    ) -> Dict[str, Any]:

        url = (
            self.base_url
            + path
        )

        headers = {
            "X-Ops-Token": self.token
        }

        try:

            response = httpx.get(
                url,
                headers=headers,
                params=params,
                timeout=15
            )

            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:

            return {
                "success": False,
                "error": (
                    f"HTTP {e.response.status_code}"
                ),
                "server_id": self.server["id"]
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e),
                "server_id": self.server["id"]
            }


def get_client(
    server_id: str
) -> MonitorSystemClient:

    server = registry.get(
        server_id
    )

    return MonitorSystemClient(
        server
    )


# ============================================================
# Tool 1
# list_servers
# ============================================================

@mcp.tool()
def list_servers(
    environment: Optional[str] = None,
    role: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取服务器列表。

    environment:
        可选，例如 production、test、development。

    role:
        可选，例如 web、database、cache。

    返回服务器基本信息，不返回 Token。
    """

    result = []

    for server in registry.all():

        if environment:
            if server.get(
                "environment"
            ) != environment:
                continue

        if role:
            if server.get(
                "role"
            ) != role:
                continue

        result.append({
            "id": server.get("id"),
            "name": server.get("name"),
            "environment": server.get(
                "environment"
            ),
            "role": server.get("role"),
            "os": server.get("os"),
            "description": server.get(
                "description"
            )
        })

    return {
        "success": True,
        "total": len(result),
        "servers": result
    }


# ============================================================
# Tool 2
# server_info
# ============================================================

@mcp.tool()
def server_info(
    server_id: str
) -> Dict[str, Any]:
    """
    获取指定服务器的信息。

    不返回监控 Token。
    """

    server = registry.get(
        server_id
    )

    return {
        "success": True,
        "data": {
            "id": server.get("id"),
            "name": server.get("name"),
            "environment": server.get(
                "environment"
            ),
            "role": server.get("role"),
            "os": server.get("os"),
            "description": server.get(
                "description"
            ),
            "monitor_system_url":
                server.get(
                    "monitor_system_url"
                )
        }
    }


# ============================================================
# Tool 3
# server_overview
# ============================================================

@mcp.tool()
def server_overview(
    server_id: str
) -> Dict[str, Any]:
    """
    获取指定服务器整体健康状态。
    """

    return get_client(
        server_id
    ).get(
        "/api/ops/overview"
    )


# ============================================================
# Tool 4
# server_status
# ============================================================

@mcp.tool()
def server_status(
    server_id: str
) -> Dict[str, Any]:
    """
    获取指定服务器当前 CPU、内存、
    磁盘和网络状态。
    """

    return get_client(
        server_id
    ).get(
        "/api/ops/status"
    )


# ============================================================
# Tool 5
# list_components
# ============================================================

@mcp.tool()
def list_components(
    server_id: str
) -> Dict[str, Any]:
    """
    获取指定服务器所有组件状态。
    """

    return get_client(
        server_id
    ).get(
        "/api/ops/components"
    )


# ============================================================
# Tool 6
# component_status
# ============================================================

@mcp.tool()
def component_status(
    server_id: str,
    name: str
) -> Dict[str, Any]:
    """
    获取指定服务器某个组件状态。

    name:
        例如 redis、rabbitmq。
    """

    return get_client(
        server_id
    ).get(
        f"/api/ops/components/{name}"
    )


# ============================================================
# Tool 7
# ssl_certificates
# ============================================================

@mcp.tool()
def ssl_certificates(
    server_id: str,
    days: int = 30
) -> Dict[str, Any]:
    """
    查询指定服务器 SSL 证书状态。

    days:
        查询未来多少天内即将过期的证书。
    """

    return get_client(
        server_id
    ).get(
        "/api/ops/ssl",
        params={
            "days": days
        }
    )


# ============================================================
# Tool 8
# api_status
# ============================================================

@mcp.tool()
def api_status(
    server_id: str
) -> Dict[str, Any]:
    """
    获取指定服务器 API 监控状态。
    """

    return get_client(
        server_id
    ).get(
        "/api/ops/apis"
    )


# ============================================================
# Tool 9
# alerts
# ============================================================

@mcp.tool()
def alerts(
    server_id: str,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取指定服务器最近的报警数据。
    """

    return get_client(
        server_id
    ).get(
        "/api/ops/alerts",
        params={
            "limit": limit
        }
    )


# ============================================================
# Tool 10
# monitor_history
# ============================================================

@mcp.tool()
def monitor_history(
    server_id: str
) -> Dict[str, Any]:
    """
    获取指定服务器历史监控数据。
    """

    return get_client(
        server_id
    ).get(
        "/api/ops/history"
    )


# ============================================================
# Tool 11
# metric_trend
# ============================================================

@mcp.tool()
def metric_trend(
    server_id: str,
    metric: str,
    hours: int = 24,
    interval: str = "1h"
) -> Dict[str, Any]:
    """
    获取指定服务器监控指标趋势。

    metric:
        cpu、memory、disk、network 等。

    hours:
        查询最近多少小时。

    interval:
        聚合间隔，例如 1h。
    """

    return get_client(
        server_id
    ).get(
        "/api/ops/trend",
        params={
            "metric": metric,
            "hours": hours,
            "interval": interval
        }
    )


# ============================================================
# Tool 12
# monitor_configs
# ============================================================

@mcp.tool()
def monitor_configs(
    server_id: str
) -> Dict[str, Any]:
    """
    获取指定服务器监控配置。
    """

    return get_client(
        server_id
    ).get(
        "/api/ops/configs"
    )


# ============================================================
# Tool 13
# scheduler_status
# ============================================================

@mcp.tool()
def scheduler_status(
    server_id: str
) -> Dict[str, Any]:
    """
    获取指定服务器 APScheduler 状态。
    """

    return get_client(
        server_id
    ).get(
        "/api/ops/scheduler"
    )


# ============================================================
# Tool 14
# fleet_overview
# ============================================================

@mcp.tool()
def fleet_overview(
    environment: Optional[str] = None,
    role: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取多台服务器总体健康状态。

    environment:
        可选，例如 production。

    role:
        可选，例如 web、database。

    适合回答：
        所有服务器有没有问题？
        生产服务器现在怎么样？
        所有数据库服务器状态如何？
    """

    servers = registry.all()

    results = []

    for server in servers:

        if environment:
            if server.get(
                "environment"
            ) != environment:
                continue

        if role:
            if server.get(
                "role"
            ) != role:
                continue

        server_id = server["id"]

        try:

            data = get_client(
                server_id
            ).get(
                "/api/ops/overview"
            )

            results.append({
                "server": {
                    "id": server_id,
                    "name": server.get(
                        "name"
                    ),
                    "environment":
                        server.get(
                            "environment"
                        ),
                    "role":
                        server.get(
                            "role"
                        )
                },
                "monitor": data
            })

        except Exception as e:

            results.append({
                "server": {
                    "id": server_id,
                    "name": server.get(
                        "name"
                    )
                },
                "monitor": {
                    "success": False,
                    "error": str(e)
                }
            })

    return {
        "success": True,
        "total": len(results),
        "servers": results
    }


# ============================================================
# Tool 15
# batch_server_status
# ============================================================

@mcp.tool()
def batch_server_status(
    server_ids: List[str]
) -> Dict[str, Any]:
    """
    批量获取多台指定服务器当前状态。

    server_ids:
        服务器 ID 数组。

    例如：

    [
        "prod-web-01",
        "prod-web-02",
        "prod-db-01"
    ]
    """

    results = []

    for server_id in server_ids:

        try:

            server = registry.get(
                server_id
            )

            data = get_client(
                server_id
            ).get(
                "/api/ops/status"
            )

            results.append({
                "server": {
                    "id": server_id,
                    "name": server.get(
                        "name"
                    ),
                    "environment":
                        server.get(
                            "environment"
                        ),
                    "role":
                        server.get(
                            "role"
                        )
                },
                "monitor": data
            })

        except Exception as e:

            results.append({
                "server": {
                    "id": server_id
                },
                "monitor": {
                    "success": False,
                    "error": str(e)
                }
            })

    return {
        "success": True,
        "total": len(results),
        "servers": results
    }


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":

    print(
        "========================================"
    )

    print(
        "System Monitor MCP Server V1.1"
    )

    print(
        f"Config: {CONFIG_FILE}"
    )

    print(
        f"Servers: {len(registry.servers)}"
    )

    print(
        f"MCP Server: "
        f"http://{MCP_HOST}:{MCP_PORT}"
    )

    print(
        "========================================"
    )

    mcp.run(
        transport="streamable-http",
        host=MCP_HOST,
        port=MCP_PORT
    )