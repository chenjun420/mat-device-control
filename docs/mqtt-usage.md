# MQTT使用指南

## 概述

MAT Device Control服务集成了MQTT支持，可以自动发现API端点并将其映射到MQTT主题，实现通过MQTT消息触发API调用。

## 配置

### 1. 启用MQTT

在`config.toml`中配置MQTT连接：

```toml
[mqtt]
enabled = true
host = "localhost"
port = 1883
# username = "your_username"  # 如果需要认证
# password = "your_password"
client_id = "mat-device-control"
topic_prefix = "mat-device-control"
qos = 1
keepalive = 60
```

### 2. 配置说明

- `enabled`: 是否启用MQTT（默认true）
- `host`: MQTT代理服务器地址
- `port`: MQTT代理服务器端口
- `username`: MQTT用户名（可选）
- `password`: MQTT密码（可选）
- `client_id`: MQTT客户端ID
- `topic_prefix`: MQTT主题前缀
- `qos`: 消息服务质量（0, 1, 2）
- `keepalive`: 心跳间隔（秒）

## MQTT主题格式

### 1. 通用API调用

```
{topic_prefix}/api/{api_path}
```

示例：
- 健康检查: `mat-device-control/api/health`
- 获取配置: `mat-device-control/api/config`
- 更新配置: `mat-device-control/api/config`

### 2. 设备相关API调用

```
{topic_prefix}/device/{device_id}/api/{api_path}
```

示例：
- 设备001的健康检查: `mat-device-control/device/001/api/health`
- 设备002的配置更新: `mat-device-control/device/002/api/config`

## 消息格式

### 请求消息

所有MQTT消息使用JSON格式：

```json
{
  "log": {
    "level": "DEBUG"
  }
}
```

### 响应消息

响应会发布到 `{原主题}/response`，格式如下：

**成功响应：**
```json
{
  "status": "success",
  "result": {
    "app": {
      "name": "mat-device-control",
      "debug": false
    },
    "log": {
      "level": "DEBUG",
      "log_dir": "logs",
      "max_bytes": 20971520,
      "backup_count": 15,
      "retention_days": 7,
      "format": "json"
    }
  },
  "original_topic": "mat-device-control/api/config"
}
```

**错误响应：**
```json
{
  "status": "error",
  "error": "API端点不存在: /unknown",
  "available_endpoints": [
    "/health",
    "/api/config"
  ]
}
```

## 使用示例

### 1. 使用MQTT客户端工具

#### 使用mosquitto_pub/sub

**订阅响应：**
```bash
mosquitto_sub -h localhost -t "mat-device-control/#" -v
```

**健康检查：**
```bash
mosquitto_pub -h localhost -t "mat-device-control/api/health" -m "{}"
```

**获取配置：**
```bash
mosquitto_pub -h localhost -t "mat-device-control/api/config" -m "{}"
```

**更新配置：**
```bash
mosquitto_pub -h localhost -t "mat-device-control/api/config" -m '{"log": {"level": "DEBUG"}}'
```

### 2. 使用Python MQTT客户端

```python
import asyncio
import json
from gmqtt import Client as MQTTClient

async def mqtt_example():
    # 创建MQTT客户端
    client = MQTTClient("python-client")
    
    # 连接到代理
    await client.connect("localhost", 1883)
    
    # 订阅响应主题
    client.subscribe("mat-device-control/api/+/response")
    
    # 发布健康检查请求
    client.publish(
        "mat-device-control/api/health",
        json.dumps({}),
        qos=1
    )
    
    # 发布配置更新请求
    client.publish(
        "mat-device-control/api/config",
        json.dumps({"log": {"level": "DEBUG"}}),
        qos=1
    )
    
    # 等待响应
    await asyncio.sleep(2)
    
    # 断开连接
    await client.disconnect()

# 运行示例
asyncio.run(mqtt_example())
```

### 3. 使用API发布MQTT消息

服务也提供了HTTP API来发布MQTT消息：

**发布消息：**
```bash
curl -X POST http://localhost:8000/api/mqtt/publish \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "device/001/api/config",
    "message": {"log": {"level": "INFO"}}
  }'
```

**查询MQTT状态：**
```bash
curl http://localhost:8000/api/mqtt/status
```

**查询API路由映射：**
```bash
curl http://localhost:8000/api/mqtt/routes
```

## 可用的API端点

通过MQTT可以访问以下API端点：

| 端点 | HTTP方法 | MQTT主题示例 | 说明 |
|------|----------|--------------|------|
| `/health` | GET | `mat-device-control/api/health` | 健康检查 |
| `/api/config` | GET | `mat-device-control/api/config` | 获取配置 |
| `/api/config` | PATCH | `mat-device-control/api/config` | 更新配置 |
| `/api/mqtt/status` | GET | `mat-device-control/api/mqtt/status` | MQTT状态 |
| `/api/mqtt/publish` | POST | `mat-device-control/api/mqtt/publish` | 发布消息 |
| `/api/mqtt/routes` | GET | `mat-device-control/api/mqtt/routes` | 路由映射 |

## 注意事项

1. **消息格式**：所有MQTT消息必须使用JSON格式
2. **QoS级别**：建议使用QoS 1确保消息至少被传递一次
3. **响应主题**：响应会发布到`{原主题}/response`
4. **设备ID**：设备主题中的device_id是可选的，用于区分不同设备
5. **错误处理**：如果API端点不存在，会在响应中返回可用端点列表

## 测试

运行MQTT相关测试：

```bash
uv run pytest tests/test_mqtt.py -v
```

## 故障排查

### 1. MQTT连接失败

检查以下项：
- MQTT代理是否运行
- 配置中的host和port是否正确
- 用户名和密码是否正确（如果需要认证）

### 2. 消息未响应

检查以下项：
- 主题格式是否正确
- 消息是否为有效JSON
- 是否订阅了响应主题（`+/response`）

### 3. API端点未找到

查看可用端点：
```bash
curl http://localhost:8000/api/mqtt/routes
```
