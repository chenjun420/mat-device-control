"""统一日志系统 - 异步写入 + 日志轮转"""

import atexit
import logging
import logging.handlers
import queue
import threading
from datetime import datetime, timezone

import orjson

from .config import config_manager


class JsonFormatter(logging.Formatter):
    """JSON 格式化器 - 使用 orjson 高性能序列化"""
    
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
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return orjson.dumps(log_data).decode("utf-8")


class AsyncLogHandler:
    """异步日志处理器管理器 - 单例模式"""
    
    _instance: "AsyncLogHandler | None" = None
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
        self._listener: logging.handlers.QueueListener | None = None
        self._file_handler: logging.Handler | None = None
        self._console_handler: logging.Handler | None = None
    
    def setup(self) -> logging.Handler:
        """设置异步日志系统"""
        log_config = config_manager.config.log
        
        log_config.log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_config.log_dir / f"{config_manager.config.name}.log"
        self._file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=log_config.max_bytes,
            backupCount=log_config.backup_count,
            encoding="utf-8",
        )
        self._file_handler.setFormatter(JsonFormatter())
        
        self._console_handler = logging.StreamHandler()
        self._console_handler.setFormatter(JsonFormatter())
        
        self._listener = logging.handlers.QueueListener(
            self._log_queue,
            self._file_handler,
            self._console_handler,
            respect_handler_level=True,
        )
        self._listener.start()
        
        atexit.register(self.shutdown)
        
        return logging.handlers.QueueHandler(self._log_queue)
    
    def shutdown(self):
        """关闭日志系统"""
        if self._listener:
            self._listener.stop()
            self._listener = None


def setup_logging() -> logging.Handler:
    """设置统一日志系统"""
    return AsyncLogHandler().setup()


def get_logger(name: str = __name__) -> logging.Logger:
    """获取 logger 实例"""
    return logging.getLogger(name)


def configure_root_logger() -> None:
    """配置根日志器"""
    queue_handler = setup_logging()
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config_manager.config.log.level))
    root_logger.addHandler(queue_handler)
    
    # 禁用 uvicorn 默认日志配置
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True


def update_log_level(level: str) -> None:
    """动态更新日志级别"""
    level_value = getattr(logging, level.upper(), None)
    if level_value is None:
        raise ValueError(f"Invalid log level: {level}")
    
    logging.getLogger().setLevel(level_value)
    config_manager.update_log_config(level=level)
    get_logger(__name__).info(f"Log level changed to {level}")


def get_current_log_level() -> str:
    """获取当前日志级别"""
    return logging.getLevelName(logging.getLogger().level)
