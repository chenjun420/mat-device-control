# 日志动态配置功能 - 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 增加日志级别动态控制，支持从 TOML 配置文件读取设置，支持通过 API 动态修改并持久化。

**Architecture:** 重构 config.py 支持可变配置和文件持久化，logging.py 新增动态更新函数，新增配置 API 路由。

**Tech Stack:** Python tomllib (标准库), FastAPI, Pydantic

---

## Task 1: 创建 TOML 配置文件

**Files:**
- Create: `config.toml`

**Step 1: 创建配置文件**

```toml
[app]
name = "mat-device-control"
debug = false

[log]
level = "INFO"
log_dir = "logs"
max_bytes = 10485760
backup_count = 10
retention_days = 7
format = "json"
```

---

## Task 2: 重构配置模块支持动态配置

**Files:**
- Modify: `modules/core/config.py`

**Step 1: 重写配置模块**

```python
"""应用配置模块 - 支持从 TOML 文件加载和动态修改"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# 配置文件路径
CONFIG_FILE = Path("config.toml")


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    log_dir: Path = Path("logs")
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 10
    retention_days: int = 7
    format: str = "json"

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "log_dir": str(self.log_dir),
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
            "retention_days": self.retention_days,
            "format": self.format,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogConfig":
        return cls(
            level=data.get("level", "INFO"),
            log_dir=Path(data.get("log_dir", "logs")),
            max_bytes=data.get("max_bytes", 10 * 1024 * 1024),
            backup_count=data.get("backup_count", 10),
            retention_days=data.get("retention_days", 7),
            format=data.get("format", "json"),
        )


@dataclass
class AppConfig:
    """应用配置"""
    name: str = "mat-device-control"
    debug: bool = False
    log: LogConfig = field(default_factory=LogConfig)

    def to_dict(self) -> dict[str, Any]:
        return {
            "app": {
                "name": self.name,
                "debug": self.debug,
            },
            "log": self.log.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        app_data = data.get("app", {})
        log_data = data.get("log", {})
        return cls(
            name=app_data.get("name", "mat-device-control"),
            debug=app_data.get("debug", False),
            log=LogConfig.from_dict(log_data),
        )


class ConfigManager:
    """配置管理器 - 单例模式"""
    
    _instance: "ConfigManager | None" = None
    _lock = __import__("threading").Lock()
    
    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._config = None
        return cls._instance
    
    @property
    def config(self) -> AppConfig:
        """获取当前配置"""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def _load_config(self) -> AppConfig:
        """从文件加载配置"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "rb") as f:
                data = tomllib.load(f)
            return AppConfig.from_dict(data)
        return AppConfig()
    
    def update_log_config(self, **kwargs) -> None:
        """更新日志配置"""
        log = self.config.log
        for key, value in kwargs.items():
            if hasattr(log, key):
                if key == "log_dir":
                    value = Path(value)
                setattr(log, key, value)
    
    def save_config(self) -> None:
        """保存配置到文件"""
        import tomli_w
        
        data = self.config.to_dict()
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(data, f)


# 全局配置管理器实例
config_manager = ConfigManager()

# 向后兼容
config = property(lambda self: config_manager.config)
```

**Step 2: 添加 tomli_w 依赖**

```bash
uv add tomli-w
```

---

## Task 3: 更新日志模块支持动态级别

**Files:**
- Modify: `modules/core/logging.py`

**Step 1: 添加动态更新函数**

在 `logging.py` 末尾添加：

```python
def update_log_level(level: str) -> None:
    """动态更新日志级别"""
    level_value = getattr(logging, level.upper(), None)
    if level_value is None:
        raise ValueError(f"Invalid log level: {level}")
    
    # 更新根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level_value)
    
    # 记录级别变更
    get_logger(__name__).info(f"Log level changed to {level}")


def get_current_log_level() -> str:
    """获取当前日志级别"""
    return logging.getLevelName(logging.getLogger().level)
```

**Step 2: 更新导入语句**

将 `from .config import config` 改为：

```python
from .config import config_manager
```

**Step 3: 更新 setup 方法中的配置引用**

将 `log_config = config.log` 改为：

```python
log_config = config_manager.config.log
```

---

## Task 4: 创建配置 API 路由

**Files:**
- Create: `modules/api/routes/config.py`

**Step 1: 创建配置路由**

```python
"""配置管理路由"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from modules.core.config import config_manager
from modules.core.logging import get_logger, update_log_level

router = APIRouter(prefix="/api/config", tags=["config"])
logger = get_logger(__name__)


class LogConfigUpdate(BaseModel):
    """日志配置更新请求"""
    level: str | None = Field(None, pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    max_bytes: int | None = Field(None, gt=0)
    backup_count: int | None = Field(None, ge=1, le=100)
    retention_days: int | None = Field(None, ge=1, le=365)
    log_dir: str | None = None
    format: str | None = Field(None, pattern="^(json|text)$")


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    log: LogConfigUpdate | None = None


class ConfigResponse(BaseModel):
    """配置响应"""
    app: dict[str, Any]
    log: dict[str, Any]


@router.get("", response_model=ConfigResponse)
async def get_config():
    """获取当前配置"""
    config = config_manager.config
    return ConfigResponse(
        app={"name": config.name, "debug": config.debug},
        log=config.log.to_dict(),
    )


@router.patch("", response_model=ConfigResponse)
async def update_config(request: ConfigUpdateRequest):
    """更新配置"""
    if request.log:
        log_updates = request.log.model_dump(exclude_unset=True)
        
        if "level" in log_updates:
            try:
                update_log_level(log_updates["level"])
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        config_manager.update_log_config(**log_updates)
        config_manager.save_config()
        
        logger.info(f"Config updated: {log_updates}")
    
    config = config_manager.config
    return ConfigResponse(
        app={"name": config.name, "debug": config.debug},
        log=config.log.to_dict(),
    )
```

---

## Task 5: 注册配置路由

**Files:**
- Modify: `main.py`

**Step 1: 添加导入**

```python
from modules.api.routes.config import router as config_router
```

**Step 2: 注册路由**

在 `app.include_router(health_router)` 后添加：

```python
app.include_router(config_router)
```

---

## Task 6: 验证功能

**Step 1: 启动服务**

```bash
uv run uvicorn main:app --reload
```

**Step 2: 获取当前配置**

```bash
curl http://localhost:8000/api/config
```

Expected: 返回当前配置 JSON

**Step 3: 修改日志级别**

```bash
curl -X PATCH http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{"log": {"level": "DEBUG"}}'
```

Expected: 返回更新后的配置，level 为 DEBUG

**Step 4: 验证配置文件更新**

```bash
cat config.toml
```

Expected: level = "DEBUG"

---

## 验证清单

- [ ] config.toml 文件存在
- [ ] GET /api/config 返回正确配置
- [ ] PATCH /api/config 可修改日志级别
- [ ] 修改后配置持久化到文件
- [ ] 日志级别实时生效
