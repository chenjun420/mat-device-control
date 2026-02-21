# FastAPI 设备控制服务 - 日志系统设计

## 概述

创建一个使用 uv 管理依赖的 FastAPI 项目，用于设备控制服务，采用模块化结构，实现统一的异步日志系统。

## 需求

- 使用 uv 管理依赖
- 单进程运行
- 统一日志到 Python 内置 logging
- 异步写入
- 日志轮转：最多 10 个文件，每个 10MB
- 保留时间：7 天

## 项目结构

```
mat-device-control/
├── pyproject.toml          # uv 项目配置
├── .python-version         # Python 版本
├── main.py                 # 入口文件
└── modules/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── config.py       # 配置管理
    │   └── logging.py      # 日志系统（核心）
    ├── api/
    │   ├── __init__.py
    │   └── routes/
    │       ├── __init__.py
    │       └── health.py   # 健康检查路由
    └── device/
        ├── __init__.py
        └── controller.py   # 设备控制模块（占位）
```

## 日志系统架构

### 技术方案

使用 `logging.handlers.QueueHandler` + `QueueListener` 实现异步写入：

```
┌─────────────────┐     ┌──────────────┐     ┌────────────────────┐
│   Application   │────▶│ QueueHandler │────▶│   QueueListener    │
│   (main thread) │     │  (non-blocking)│    │  (background thread)│
└─────────────────┘     └──────────────┘     └────────────────────┘
                                                      │
                                                      ▼
                                            ┌────────────────────┐
                                            │ RotatingFileHandler │
                                            │   (JSON format)    │
                                            └────────────────────┘
```

### 配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| max_bytes | 10MB | 单文件最大大小 |
| backup_count | 10 | 最多保留文件数 |
| retention_days | 7 | 日志保留天数 |
| log_dir | logs | 日志目录 |
| format | json | JSON 格式 |

### 日志格式

```json
{
  "timestamp": "2024-02-21T21:45:13.123+08:00",
  "level": "INFO",
  "logger": "modules.device.controller",
  "message": "Device connected",
  "module": "controller",
  "function": "connect",
  "line": 42
}
```

### 生命周期管理

1. **启动时**：在 FastAPI `lifespan` 中初始化 QueueListener
2. **运行时**：所有模块通过 `logging.getLogger(__name__)` 获取 logger
3. **关闭时**：在 lifespan 退出时调用 `listener.stop()`

## 依赖

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "python-dateutil>=2.9.0",  # 时区处理
]
```

## 运行方式

```bash
# 开发
uv run uvicorn main:app --reload

# 生产（单进程）
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```
