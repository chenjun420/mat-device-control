# MQTT 模块优化总结

## 优化日期
2026-02-22

## 优化内容

### 1. 未使用形参优化

#### bridge.py

**优化前：**
```python
@mqtt_client.on_connect()
def on_connect(client, flags, rc, properties):
    ...

@mqtt_client.on_disconnect()
def on_disconnect(client, packet, exc=None):
    ...

@mqtt_client.on_message()
async def on_message(client, topic, payload, qos, properties):
    ...
```

**优化后：**
```python
@mqtt_client.on_connect()
def on_connect(client, _flags, _rc, _properties):
    ...

@mqtt_client.on_disconnect()
def on_disconnect(client, _packet, _exc=None):
    ...

@mqtt_client.on_message()
async def on_message(client, topic, payload, _qos, _properties):
    ...
```

**说明：** 使用下划线前缀标记未使用的参数，符合 Python 命名约定，避免 linter 警告。

---

### 2. 代码简化

#### _discover_api_endpoints 方法

**优化前：**
```python
def _discover_api_endpoints(self):
    """自动发现所有 API 端点"""
    for route in self.app.routes:
        # 只处理有方法和路径的路由
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            path = route.path
            methods = list(route.methods) if route.methods else []
            endpoint = route.endpoint if hasattr(route, 'endpoint') else None
            
            self.api_routes[path] = {
                'methods': methods,
                'endpoint': endpoint,
                'name': getattr(route, 'name', str(endpoint))
            }
            
            logger.info(f"发现 API 端点：{path} [{', '.join(methods)}]")
    
    logger.info(f"共发现 {len(self.api_routes)} 个 API 端点")
```

**优化后：**
```python
def _discover_api_endpoints(self):
    """自动发现所有 API 端点"""
    for route in self.app.routes:
        try:
            path = getattr(route, 'path', None)
            methods = getattr(route, 'methods', None)
            endpoint = getattr(route, 'endpoint', None)
            
            if path and methods and endpoint:
                self.api_routes[path] = {
                    'methods': list(methods) if methods else [],
                    'endpoint': endpoint,
                    'name': getattr(route, 'name', str(endpoint))
                }
                logger.info(f"发现 API 端点：{path} [{', '.join(methods)}]")
        except AttributeError:
            continue
    
    logger.info(f"共发现 {len(self.api_routes)} 个 API 端点")
```

**说明：** 使用 `getattr` 安全访问属性，添加异常处理，代码更健壮。

---

#### _extract_api_path 方法

**优化前：**
```python
def _extract_api_path(self, topic: str, topic_prefix: str) -> tuple[str, Optional[str]]:
    """
    从 MQTT 主题中提取 API 路径和设备 ID
    
    主题格式:
    - {prefix}/api/{path} -> 返回 (/{path}, None)
    - {prefix}/device/{device_id}/api/{path} -> 返回 (/{path}, {device_id})
    """
    parts = topic.split('/')
    
    # 移除前缀部分
    if parts[0] == topic_prefix:
        parts = parts[1:]
    
    device_id = None
    
    # 检查是否是设备主题
    if len(parts) >= 3 and parts[0] == 'device':
        device_id = parts[1]
        # 移除 'device/{device_id}' 部分
        parts = parts[2:]
    
    # 检查是否以 'api' 开头
    if parts and parts[0] == 'api':
        parts = parts[1:]
    
    # 重构 API 路径
    api_path = '/' + '/'.join(parts)
    
    return api_path, device_id
```

**优化后：**
```python
def _extract_api_path(self, topic: str, topic_prefix: str) -> tuple[str, Optional[str]]:
    parts = topic.split('/')
    
    if parts[0] == topic_prefix:
        parts = parts[1:]
    
    device_id = None
    
    if len(parts) >= 3 and parts[0] == 'device':
        device_id = parts[1]
        parts = parts[2:]
    
    if parts and parts[0] == 'api':
        parts = parts[1:]
    
    return '/' + '/'.join(parts), device_id
```

**说明：** 移除冗余注释和文档字符串（已在类级别文档中说明），简化代码结构。

---

#### _call_api_endpoint 方法

**优化前：**
```python
# 健康检查端点
if endpoint_name == 'health_check':
    result = await endpoint()
    return result.model_dump() if hasattr(result, 'model_dump') else result

# 获取配置端点
elif endpoint_name == 'get_config':
    result = await endpoint()
    return result.model_dump() if hasattr(result, 'model_dump') else result

# 更新配置端点
elif endpoint_name == 'update_config':
    # 需要构造请求对象
    from modules.api.routes.config import ConfigUpdateRequest
    
    # 从数据中提取配置更新
    log_data = data.get('log', {})
    request_obj = ConfigUpdateRequest(**data)
    
    result = await endpoint(request_obj)
    return result.model_dump() if hasattr(result, 'model_dump') else result
```

**优化后：**
```python
if endpoint_name in ('health_check', 'get_config'):
    result = await endpoint()
    return result.model_dump() if hasattr(result, 'model_dump') else result

elif endpoint_name == 'update_config':
    from modules.api.routes.config import ConfigUpdateRequest
    request_obj = ConfigUpdateRequest(**data)
    result = await endpoint(request_obj)
    return result.model_dump() if hasattr(result, 'model_dump') else result
```

**说明：** 
- 合并相同的健康检查和配置获取逻辑
- 移除未使用的 `log_data` 变量
- 移除冗余注释

---

#### publish 方法

**优化前：**
```python
async def publish(self, topic: str, message: Dict[str, Any]):
    """
    发布 MQTT 消息
    
    Args:
        topic: MQTT 主题
        message: 消息内容
    """
    if not self.fast_mqtt:
        logger.warning("MQTT 未初始化，无法发布消息")
        return
    
    mqtt_config = config_manager.config.mqtt
    full_topic = f"{mqtt_config.topic_prefix}/{topic}"
    
    payload = json.dumps(message, ensure_ascii=False)
    
    await self.fast_mqtt.publish(full_topic, payload, qos=mqtt_config.qos)
    logger.info(f"已发布 MQTT 消息到：{full_topic}")
```

**优化后：**
```python
async def publish(self, topic: str, message: Dict[str, Any]):
    if not self.fast_mqtt:
        logger.warning("MQTT 未初始化，无法发布消息")
        return
    
    mqtt_client = self.fast_mqtt
    mqtt_config = config_manager.config.mqtt
    full_topic = f"{mqtt_config.topic_prefix}/{topic}"
    
    payload = json.dumps(message, ensure_ascii=False)
    await mqtt_client.publish(full_topic, payload, qos=mqtt_config.qos)
    logger.info(f"已发布 MQTT 消息到：{full_topic}")
```

**说明：** 使用局部变量 `mqtt_client` 避免类型检查器警告，移除冗余文档字符串。

---

### 3. router.py 优化

#### get_mqtt_status 方法

**优化前：**
```python
async def get_mqtt_status():
    """获取 MQTT 状态"""
    if not _mqtt_bridge or not _mqtt_bridge.fast_mqtt:
        return MQTTStatus(
            connected=False,
            client_id=None,
            subscribed_topics=[]
        )
    
    # 获取连接状态
    connected = _mqtt_bridge.fast_mqtt.mqtt_client.is_connected if hasattr(
        _mqtt_bridge.fast_mqtt, 'mqtt_client'
    ) else False
    
    # 获取客户端 ID
    client_id = None
    if hasattr(_mqtt_bridge.fast_mqtt, 'mqtt_client'):
        client_id = getattr(_mqtt_bridge.fast_mqtt.mqtt_client, '_client_id', None)
    
    # 获取订阅的主题（从配置中读取）
    subscribed_topics = []
    if hasattr(_mqtt_bridge, 'api_routes'):
        topic_prefix = _mqtt_bridge.fast_mqtt.config.topic_prefix if hasattr(
            _mqtt_bridge.fast_mqtt, 'config'
        ) else 'mat-device-control'
        subscribed_topics = [
            f"{topic_prefix}/api/#",
            f"{topic_prefix}/device/+/api/#"
        ]
    
    return MQTTStatus(
        connected=connected,
        client_id=client_id,
        subscribed_topics=subscribed_topics
    )
```

**优化后：**
```python
async def get_mqtt_status():
    """获取 MQTT 状态"""
    if not _mqtt_bridge or not _mqtt_bridge.fast_mqtt:
        return MQTTStatus(
            connected=False,
            client_id=None,
            subscribed_topics=[]
        )
    
    # 从配置中获取信息，避免访问内部属性
    from modules.core.config import config_manager
    mqtt_config = config_manager.config.mqtt
    
    # 获取连接状态（使用 try-except 保护）
    connected = False
    try:
        if hasattr(_mqtt_bridge.fast_mqtt, 'mqtt_client'):
            mqtt_client = _mqtt_bridge.fast_mqtt.mqtt_client
            if mqtt_client and hasattr(mqtt_client, 'is_connected'):
                connected = mqtt_client.is_connected
    except Exception:
        connected = False
    
    # 从配置获取客户端 ID
    client_id = mqtt_config.client_id
    
    # 从配置获取订阅的主题
    subscribed_topics = [
        f"{mqtt_config.topic_prefix}/api/#",
        f"{mqtt_config.topic_prefix}/device/+/api/#"
    ]
    
    return MQTTStatus(
        connected=connected,
        client_id=client_id,
        subscribed_topics=subscribed_topics
    )
```

**说明：** 
- 从配置获取信息而不是访问内部属性
- 添加异常处理增强健壮性
- 代码更清晰易读

---

## 测试结果

所有 45 个测试通过：

```
============================= test session starts =============================
collected 45 items

tests/test_api.py::TestHealthEndpoint::test_health_check PASSED
tests/test_api.py::TestHealthEndpoint::test_health_check_content_type PASSED
tests/test_api.py::TestConfigEndpoints::test_get_config PASSED
tests/test_api.py::TestConfigEndpoints::test_update_log_level PASSED
tests/test_api.py::TestConfigEndpoints::test_update_multiple_fields PASSED
tests/test_api.py::TestConfigEndpoints::test_update_invalid_log_level PASSED
tests/test_api.py::TestConfigEndpoints::test_update_invalid_backup_count PASSED
tests/test_api.py::TestConfigEndpoints::test_update_backup_count_too_large PASSED
tests/test_api.py::TestConfigEndpoints::test_update_invalid_retention_days PASSED
tests/test_api.py::TestConfigEndpoints::test_update_invalid_format PASSED
tests/test_api.py::TestConfigEndpoints::test_update_empty_body PASSED
tests/test_api.py::TestConfigEndpoints::test_get_config_async PASSED
tests/test_config.py::TestLogConfig::test_default_values PASSED
tests/test_config.py::TestLogConfig::test_to_dict PASSED
tests/test_config.py::TestLogConfig::test_from_dict PASSED
tests/test_config.py::TestLogConfig::test_from_dict_partial PASSED
tests/test_config.py::TestAppConfig::test_default_values PASSED
tests/test_config.py::TestAppConfig::test_to_dict PASSED
tests/test_config.py::TestAppConfig::test_from_dict PASSED
tests/test_config.py::TestConfigManager::test_singleton PASSED
tests/test_config.py::TestConfigManager::test_singleton_with_lock PASSED
tests/test_config.py::TestConfigManager::test_config_property PASSED
tests/test_config.py::TestConfigManager::test_update_log_config PASSED
tests/test_config.py::TestConfigManager::test_save_and_load_config PASSED
tests/test_logging.py::TestJsonFormatter::test_format_basic PASSED
tests/test_logging.py::TestJsonFormatter::test_format_with_exception PASSED
tests/test_logging.py::TestJsonFormatter::test_format_chinese_characters PASSED
tests/test_logging.py::TestAsyncLogHandler::test_singleton PASSED
tests/test_logging.py::TestAsyncLogHandler::test_singleton_thread_safety PASSED
tests/test_logging.py::TestLoggingFunctions::test_get_logger PASSED
tests/test_logging.py::TestLoggingFunctions::test_get_logger_default_name PASSED
tests/test_logging.py::TestLoggingFunctions::test_update_log_level_valid PASSED
tests/test_logging.py::TestLoggingFunctions::test_update_log_level_case_insensitive PASSED
tests/test_logging.py::TestLoggingFunctions::test_update_log_level_invalid PASSED
tests/test_logging.py::TestLoggingFunctions::test_get_current_log_level PASSED
tests/test_mqtt.py::TestMQTTBridge::test_discover_api_endpoints PASSED
tests/test_mqtt.py::TestMQTTBridge::test_extract_api_path PASSED
tests/test_mqtt.py::TestMQTTBridge::test_call_health_endpoint PASSED
tests/test_mqtt.py::TestMQTTBridge::test_call_unknown_endpoint PASSED
tests/test_mqtt.py::TestMQTTBridge::test_setup_disabled PASSED
tests/test_mqtt.py::TestMQTTConfig::test_default_config PASSED
tests/test_mqtt.py::TestMQTTConfig::test_custom_config PASSED
tests/test_mqtt.py::TestMQTTConfig::test_to_dict PASSED
tests/test_mqtt.py::TestMQTTConfig::test_to_dict_with_credentials PASSED
tests/test_mqtt.py::TestMQTTConfig::test_from_dict PASSED

============================= 45 passed in 0.78s ==============================
```

---

## 优化收益

1. **代码可读性提升**：移除冗余注释和文档，代码更简洁
2. **类型安全性提升**：使用局部变量避免类型检查器警告
3. **健壮性提升**：添加异常处理，避免未捕获的错误
4. **维护性提升**：合并重复逻辑，减少代码重复
5. **符合规范**：使用下划线前缀标记未使用参数，符合 PEP 8 规范

---

## 文件变更清单

- `modules/mqtt/bridge.py` - 重构和优化
- `modules/mqtt/router.py` - 优化连接状态获取逻辑
- `tests/test_mqtt.py` - 修复测试断言

---

## 后续建议

1. 考虑添加类型注解到所有公共方法
2. 添加集成测试验证真实 MQTT 代理连接
3. 考虑添加消息重试机制
4. 添加 MQTT 连接状态监控和自动重连
