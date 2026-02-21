"""FastAPI 设备控制服务入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from modules.api.routes.health import router as health_router
from modules.api.routes.config import router as config_router
from modules.core.config import config_manager
from modules.core.exceptions import register_exception_handlers
from modules.core.logging import configure_root_logger, get_logger
from modules.core.response import OrjsonResponse, ResponseMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    configure_root_logger()
    logger = get_logger(__name__)
    logger.info("Application starting up", extra={"app_name": config_manager.config.name})
    
    yield
    
    logger.info("Application shutting down")


app = FastAPI(
    title="MAT Device Control API",
    description="""
## 设备控制服务 API

基于 FastAPI 的设备控制服务，支持异步日志系统和动态配置管理。

### 功能特性

* **异步日志系统** - 使用 QueueHandler + QueueListener 实现非阻塞日志写入
* **日志轮转** - 支持按文件大小和备份数量自动轮转
* **动态配置** - 支持通过 API 实时修改日志级别和配置参数
* **配置持久化** - 配置修改自动保存到 TOML 文件
* **高性能 JSON** - 使用 orjson 进行 JSON 序列化

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
| `/api/config` | 配置管理 |

### 访问地址

* **Swagger UI**: `/docs`
* **ReDoc**: `/redoc`
* **OpenAPI JSON**: `/openapi.json`
""",
    version="0.1.0",
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


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config_manager.config.debug,
    )
