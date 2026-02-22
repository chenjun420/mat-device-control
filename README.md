# MAT Device Control

基于 FastAPI 的设备控制服务，支持异步日志系统、动态配置管理和MQTT通信。

## 特性

- **异步日志系统**：使用 `QueueHandler` + `QueueListener` 实现非阻塞日志写入
- **日志轮转**：支持按文件大小（10MB）和备份数量（10个）自动轮转
- **动态配置**：支持通过 API 实时修改日志级别和配置参数
- **配置持久化**：配置修改自动保存到 TOML 文件
- **JSON 日志格式**：结构化日志，便于日志系统收集分析
- **MQTT支持**：自动发现API端点并映射到MQTT主题，实现基于消息队列的设备控制

## 项目结构

```
mat-device-control/
├── config.toml             # 配置文件
├── main.py                 # 应用入口
├── pyproject.toml          # 项目配置
└── modules/
    ├── core/
    │   ├── config.py       # 配置管理
    │   └── logging.py      # 日志系统
    ├── api/routes/
    │   ├── health.py       # 健康检查
    │   └── config.py       # 配置 API
    ├── mqtt/
    │   ├── bridge.py       # MQTT桥接器
    │   └── router.py       # MQTT路由
    └── device/
        └── controller.py   # 设备控制器
```

## 快速开始

### 环境要求

- Python >= 3.12
- uv 包管理器

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd mat-device-control

# 安装依赖
uv sync
```

### 运行

```bash
# 开发模式（热重载）
uv run uvicorn main:app --reload

# 生产模式（单进程）
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

## 配置

### 配置文件 (config.toml)

```toml
[app]
name = "mat-device-control"
debug = false

[log]
level = "INFO"              # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_dir = "logs"            # 日志目录
max_bytes = 10485760        # 单文件最大 10MB
backup_count = 10           # 最多保留 10 个文件
retention_days = 7          # 保留 7 天
format = "json"             # 日志格式: json, text
```

## API 文档

启动服务后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/config` | 获取当前配置 |
| PATCH | `/api/config` | 更新配置 |
| GET | `/api/mqtt/status` | 获取MQTT状态 |
| POST | `/api/mqtt/publish` | 发布MQTT消息 |
| GET | `/api/mqtt/routes` | 获取API路由映射 |

### 示例

**健康检查**

```bash
curl http://localhost:8000/health
# {"status": "healthy", "service": "mat-device-control"}
```

**获取配置**

```bash
curl http://localhost:8000/api/config
# {
#   "app": {"name": "mat-device-control", "debug": false},
#   "log": {"level": "INFO", "log_dir": "logs", ...}
# }
```

**更新日志级别**

```bash
curl -X PATCH http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{"log": {"level": "DEBUG"}}'
```

**更新多个配置**

```bash
curl -X PATCH http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{"log": {"level": "WARNING", "max_bytes": 20971520, "backup_count": 20}}'
```

## 日志格式

日志以 JSON 格式输出：

```json
{
  "timestamp": "2024-02-21T14:48:56.752102+00:00",
  "level": "INFO",
  "logger": "main",
  "message": "Application starting up",
  "module": "main",
  "function": "lifespan",
  "line": 18
}
```

## 测试

```bash
# 运行所有测试
uv run pytest

# 详细输出
uv run pytest -v

# 运行特定测试
uv run pytest tests/test_api.py

# 测试覆盖率
uv run pytest --cov=modules
```

### 测试覆盖

- 配置模块：LogConfig、AppConfig、ConfigManager、MQTTConfig
- 日志模块：JsonFormatter、AsyncLogHandler、日志函数
- API 路由：健康检查、配置 CRUD、参数验证
- MQTT 模块：MQTTBridge、API端点发现、主题映射

## MQTT 使用

### MQTT 配置

在 `config.toml` 中配置 MQTT：

```toml
[mqtt]
enabled = true
host = "localhost"
port = 1883
# username = "your_username"  # 可选
# password = "your_password"  # 可选
client_id = "mat-device-control"
topic_prefix = "mat-device-control"
qos = 1
keepalive = 60
```

### MQTT 主题格式

**通用 API 调用：**
- `mat-device-control/api/health` - 健康检查
- `mat-device-control/api/config` - 获取/更新配置

**设备相关 API 调用：**
- `mat-device-control/device/{device_id}/api/health` - 设备健康检查
- `mat-device-control/device/{device_id}/api/config` - 设备配置

### MQTT 示例

**订阅响应：**
```bash
mosquitto_sub -h localhost -t "mat-device-control/#" -v
```

**健康检查：**
```bash
mosquitto_pub -h localhost -t "mat-device-control/api/health" -m "{}"
```

**更新配置：**
```bash
mosquitto_pub -h localhost -t "mat-device-control/api/config" \
  -m '{"log": {"level": "DEBUG"}}'
```

详细使用说明请参考 [MQTT使用指南](docs/mqtt-usage.md)。

## 开发

### 添加新依赖

```bash
# 运行时依赖
uv add <package>

# 开发依赖
uv add --dev <package>
```

### 代码风格

推荐使用以下工具：

```bash
uv add --dev ruff mypy

# 格式化
uv run ruff format .

# 类型检查
uv run mypy modules/
```

## License

MIT