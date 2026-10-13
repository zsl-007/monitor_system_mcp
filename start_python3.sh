#!/bin/bash

# 进入工作目录
cd /home/monitor_system_mcp

# 激活虚拟环境
source /home/monitor_system/MonitorSystemEnv/bin/activate

# 启动应用
python3 server.py
