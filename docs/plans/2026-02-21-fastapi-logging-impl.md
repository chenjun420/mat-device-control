# FastAPI 设备控制服务 - 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建一个使用 uv 管理依赖的 FastAPI 设备控制服务，实现异步日志系统。

**Architecture:** 模块化结构，核心日志模块使用 QueueHandler + QueueListener 实现异步写入，RotatingFileHandler 实现日志轮转。

**Tech Stack:** FastAPI, uvicorn, Python logging, uv

---

## Task 1: 初始化 uv 项目

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`

**Step 1: 初始化 uv 项目**

```bash
uv init --name mat-device-control
```

**Step 2: 设置 Python 版本**

```bash
uv python pin 3.14
```

**Step 3: 添加依赖**

```bash
uv add fastapi uvicorn python-dateutil
```

**Step 4: 验证项目结构**

Run: `ls -la`
Expected: pyproject.toml, .python-version 文件存在

---

## Task 2: 创建模块目录结构

**Files:**
- Create: `modules/__init__.py`
- Create: `modules/core/__init__.py`
- Create: `modules/core/config.py`
- Create: `modules/core/logging.py`
- Create: `modules/api/__init__.py`
- Create: `modules/api/routes/__init__.py`
- Create: `modules/api/routes/health.py`
- Create: `modules/device/__init__.py`
- Create: `modules/device/controller.py`

**Step 1: 创建目录结构**

```bash
mkdir -p modules/core modules/api/routes modules/device
```

**Step 2: 创建 __init__.py 文件**

```bash
touch modules/__init__.py modules/core/__init__.py modules/api/__init__.py modules/api/routes/__init__.py modules/device/__init__.py
```

---

## Task 3: 实现配置模块

**Files:**
- Create: `modules/core/config.py`

**Step 1: 编写配置模块**

```python
"""应用配置模块"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LogConfig:
    """日志配置"""
    log_dir: Path = Path("logs")
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 10
    retention_days: int = 7
    format: str = "json"
    level: str = "INFO"


@dataclass(frozen=True)
class AppConfig:
    """应用配置"""
    app_name: str = "mat-device-control"
    debug: bool = False
    log: LogConfig = LogConfig()


# 全局配置实例
config = AppConfig()
```

**Step 2: 验证语法**

Run: `uv run python -c "from modules.core.config import config; print(config)"`
Expected: 输出配置信息

---

## Task 4: 实现异步日志系统

**Files:**
- Create: `modules/core/logging.py`

**Step 1: 编写日志系统**

```python
"""统一日志系统 - 异步写入 + 日志轮转"""

import atexit
import json
import logging
import logging.handlers
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import config


class JsonFormatter(logging.Formatter):
    """JSON 格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class AsyncLogHandler:
    """异步日志处理器管理器"""
    
    _instance: Optional["AsyncLogHandler"] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "AsyncLogHandler":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._log_queue: queue.Queue[logging.LogRecord] = queue.Queue(maxsize=10000)
        self._listener: Optional[logging.handlers.QueueListener] = None
        self._file_handler: Optional[logging.Handler] = None
        self._console_handler: Optional[logging.Handler] = None
    
    def setup(self) -> logging.Handler:
        """设置异步日志系统，返回 QueueHandler"""
        log_config = config.log
        
        # 确保日志目录存在
        log_config.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建文件处理器 - RotatingFileHandler
        log_file = log_config.log_dir / f"{config.app_name}.log"
        self._file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=log_config.max_bytes,
            backupCount=log_config.backup_count,
            encoding="utf-8",
        )
        self._file_handler.setFormatter(JsonFormatter())
        
        # 创建控制台处理器
        self._console_handler = logging.StreamHandler()
        self._console_handler.setFormatter(JsonFormatter())
        
        # 创建 QueueListener（后台线程处理日志写入）
        self._listener = logging.handlers.QueueListener(
            self._log_queue,
            self._file_handler,
            self._console_handler,
            respect_handler_level=True,
        )
        self._listener.start()
        
        # 注册退出时的清理
        atexit.register(self.shutdown)
        
        # 返回 QueueHandler 供应用使用
        queue_handler = logging.handlers.QueueHandler(self._log_queue)
        return queue_handler
    
    def shutdown(self):
        """关闭日志系统"""
        if self._listener:
            self._listener.stop()
            self._listener = None


def setup_logging() -> logging.Handler:
    """设置统一日志系统"""
    async_handler = AsyncLogHandler()
    queue_handler = async_handler.setup()
    return queue_handler


def get_logger(name: str = __name__) -> logging.Logger:
    """获取 logger 实例"""
    return logging.getLogger(name)


def configure_root_logger() -> None:
    """配置根日志器"""
    queue_handler = setup_logging()
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log.level))
    root_logger.addHandler(queue_handler)
    
    # 禁用 uvicorn 默认的日志配置，使用我们的
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
```

**Step 2: 验证语法**

Run: `uv run python -c "from modules.core.logging import setup_logging; print('OK')"`
Expected: 输出 OK

---

## Task 5: 实现健康检查路由

**Files:**
- Create: `modules/api/routes/health.py`

**Step 1: 编写健康检查路由**

```python
"""健康检查路由"""

from fastapi import APIRouter

from modules.core.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
async def health_check():
    """健康检查端点"""
    logger.info("Health check requested")
    return {"status": "healthy", "service": "mat-device-control"}
```

---

## Task 6: 实现设备控制器占位模块

**Files:**
- Create: `modules/device/controller.py`

**Step 1: 编写设备控制器**

```python
"""设备控制器模块"""

from modules.core.logging import get_logger

logger = get_logger(__name__)


class DeviceController:
    """设备控制器（占位实现）"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        logger.info(f"Device controller initialized", extra={"device_id": device_id})
    
    async def connect(self) -> bool:
        """连接设备"""
        logger.info(f"Connecting to device", extra={"device_id": self.device_id})
        return True
    
    async def disconnect(self) -> None:
        """断开设备连接"""
        logger.info(f"Disconnecting from device", extra={"device_id": self.device_id})
```

---

## Task 7: 实现主入口文件

**Files:**
- Create: `main.py`

**Step 1: 编写主入口**

```python
"""FastAPI 设备控制服务入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from modules.api.routes.health import router as health_router
from modules.core.config import config
from modules.core.logging import configure_root_logger, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：初始化日志系统
    configure_root_logger()
    logger = get_logger(__name__)
    logger.info("Application starting up", extra={"app_name": config.app_name})
    
    yield
    
    # 关闭时：日志已在 atexit 中处理
    logger.info("Application shutting down")


app = FastAPI(
    title=config.app_name,
    description="设备控制服务",
    version="0.1.0",
    lifespan=lifespan,
)

# 注册路由
app.include_router(health_router)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.debug,
    )
```

---

## Task 8: 验证项目运行

**Step 1: 启动服务**

Run: `uv run python main.py`
Expected: 服务启动，日志输出到控制台和 logs/ 目录

**Step 2: 测试健康检查**

Run: `curl http://localhost:8000/health`
Expected: `{"status": "healthy", "service": "mat-device-control"}`

**Step 3: 检查日志文件**

Run: `cat logs/mat-device-control.log`
Expected: JSON 格式的日志记录

---

## Task 9: 清理临时文件

**Step 1: 删除 nul 文件**

```bash
rm nul
```

---

## 验证清单

- [ ] uv 项目正确初始化
- [ ] 依赖正确安装
- [ ] 模块目录结构完整
- [ ] 日志系统异步写入正常
- [ ] 日志轮转配置正确（10MB × 10 文件）
- [ ] 日志格式为 JSON
- [ ] FastAPI 服务正常启动
- [ ] 健康检查端点正常工作
