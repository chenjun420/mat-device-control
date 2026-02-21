"""应用配置模块 - 支持从 TOML 文件加载和动态修改"""

import threading
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_FILE = Path("config.toml")


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    max_bytes: int = 10 * 1024 * 1024
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
            "app": {"name": self.name, "debug": self.debug},
            "log": self.log.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        return cls(
            name=data.get("app", {}).get("name", "mat-device-control"),
            debug=data.get("app", {}).get("debug", False),
            log=LogConfig.from_dict(data.get("log", {})),
        )


class ConfigManager:
    """配置管理器 - 单例模式"""
    
    _instance: "ConfigManager | None" = None
    _lock = threading.Lock()
    _config: "AppConfig | None" = None
    
    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def config(self) -> AppConfig:
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    @staticmethod
    def _load_config() -> AppConfig:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "rb") as f:
                return AppConfig.from_dict(tomllib.load(f))
        return AppConfig()
    
    def update_log_config(self, **kwargs) -> None:
        log = self.config.log
        for key, value in kwargs.items():
            if hasattr(log, key):
                setattr(log, key, Path(value) if key == "log_dir" else value)
    
    def save_config(self) -> None:
        import tomli_w
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(self.config.to_dict(), f)


config_manager = ConfigManager()

# 兼容性别名
config = config_manager.config
