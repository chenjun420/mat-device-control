"""FastAPI 设备控制服务入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from modules.api.routes.health import router as health_router
from modules.api.routes.config import router as config_router
from modules.mqtt.router import router as mqtt_router, set_mqtt_bridge
from modules.mqtt.bridge import MQTTBridge
from modules.core.config import config_manager
from modules.core.exceptions import register_exception_handlers
from modules.core.logging import configure_root_logger, get_logger
from modules.core.response import OrjsonResponse, ResponseMiddleware


# 全局MQTT桥接器
mqtt_bridge = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期管理"""
    global mqtt_bridge
    
    configure_root_logger()
    logger = get_logger(__name__)
    logger.info("Application starting up", extra={"app_name": config_manager.config.name})
    
    # 初始化MQTT桥接器
    if config_manager.config.mqtt.enabled:
        mqtt_bridge = MQTTBridge(app)
        mqtt_bridge.setup()
        set_mqtt_bridge(mqtt_bridge)
        logger.info("MQTT bridge initialized")
        
        # 主动连接 MQTT
        connected = await mqtt_bridge.connect()
        if connected:
            logger.info("MQTT connected successfully")
        else:
            logger.warning("MQTT connection failed, will retry on message handling")
    
    yield
    
    # 清理MQTT连接
    if mqtt_bridge:
        logger.info("Disconnecting MQTT...")
        await mqtt_bridge.disconnect()
    
    logger.info("Application shutting down")


app = FastAPI(
    title="MAT Device Control API",
    description="""
## 设备控制服务 API

基于 FastAPI 的设备控制服务，支持异步日志系统、动态配置管理和MQTT通信。

### 功能特性

* **异步日志系统** - 使用 QueueHandler + QueueListener 实现非阻塞日志写入
* **日志轮转** - 支持按文件大小和备份数量自动轮转
* **动态配置** - 支持通过 API 实时修改日志级别和配置参数
* **配置持久化** - 配置修改自动保存到 TOML 文件
* **高性能 JSON** - 使用 orjson 进行 JSON 序列化
* **MQTT支持** - 自动发现API端点并映射到MQTT主题

### 统一响应格式

所有 API 响应采用统一的 JSON 格式：

```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### API 端点

| 端点 | 描述 |
|------|------|
| `/health` | 健康检查 |
| `/config` | 配置管理 |
| `/mqtt/status` | MQTT状态查询 |
| `/mqtt/publish` | MQTT消息发布 |
| `/mqtt/routes` | API路由映射查询 |

### MQTT 主题格式

MQTT消息支持以下主题格式：

* `mat-device-control/{path}` - 直接API调用（匹配HTTP路由）
* `mat-device-control/device/{device_id}/{path}` - 设备相关API调用

响应会发布到 `response/{原主题}`

### 访问地址

* **Swagger UI**: `/docs`
* **ReDoc**: `/redoc`
* **OpenAPI JSON**: `/openapi.json`
""",
    version="0.2.0",
    lifespan=lifespan,
    default_response_class=OrjsonResponse,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "MAT Device Control", "email": "support@example.com"},
    license_info={"name": "MIT"},
)

# 注册全局异常处理器
register_exception_handlers(app)

# 注册响应拦截中间件
app.add_middleware(ResponseMiddleware)

# 注册路由
app.include_router(health_router)
app.include_router(config_router)
app.include_router(mqtt_router)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config_manager.config.debug,
    )
