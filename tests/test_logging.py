"""日志模块单元测试"""

import json
import logging

import pytest

from modules.core.logging import (
    JsonFormatter,
    AsyncLogHandler,
    get_logger,
    update_log_level,
    get_current_log_level,
)


class TestJsonFormatter:
    """JsonFormatter 测试类"""

    def test_format_basic(self):
        """测试基本日志格式化"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"  # 手动设置函数名
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert data["module"] == "test"
        assert data["function"] == "test_function"
        assert data["line"] == 42
        assert "timestamp" in data

    def test_format_with_exception(self):
        """测试带异常信息的日志格式化"""
        formatter = JsonFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=50,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "ValueError: Test error" in data["exception"]

    def test_format_chinese_characters(self):
        """测试中文字符格式化"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=60,
            msg="中文测试消息",
            args=(),
            exc_info=None,
        )
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["message"] == "中文测试消息"


class TestAsyncLogHandler:
    """AsyncLogHandler 测试类"""

    def test_singleton(self):
        """测试单例模式"""
        handler1 = AsyncLogHandler()
        handler2 = AsyncLogHandler()
        
        assert handler1 is handler2

    def test_singleton_thread_safety(self):
        """测试单例模式线程安全"""
        import threading
        
        instances = []
        
        def create_instance():
            instances.append(AsyncLogHandler())
        
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert all(inst is instances[0] for inst in instances)


class TestLoggingFunctions:
    """日志函数测试类"""

    def test_get_logger(self):
        """测试获取 logger"""
        logger = get_logger("test.module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_logger_default_name(self):
        """测试获取 logger 默认名称"""
        logger = get_logger()
        
        assert isinstance(logger, logging.Logger)

    def test_update_log_level_valid(self):
        """测试更新日志级别（有效值）"""
        # 设置初始级别
        logging.getLogger().setLevel(logging.INFO)
        
        # 更新为 DEBUG
        update_log_level("DEBUG")
        assert logging.getLogger().level == logging.DEBUG
        
        # 更新为 WARNING
        update_log_level("WARNING")
        assert logging.getLogger().level == logging.WARNING

    def test_update_log_level_case_insensitive(self):
        """测试更新日志级别（大小写不敏感）"""
        logging.getLogger().setLevel(logging.INFO)
        
        update_log_level("error")
        assert logging.getLogger().level == logging.ERROR

    def test_update_log_level_invalid(self):
        """测试更新日志级别（无效值）"""
        with pytest.raises(ValueError, match="Invalid log level"):
            update_log_level("INVALID_LEVEL")

    def test_get_current_log_level(self):
        """测试获取当前日志级别"""
        logging.getLogger().setLevel(logging.DEBUG)
        assert get_current_log_level() == "DEBUG"
        
        logging.getLogger().setLevel(logging.WARNING)
        assert get_current_log_level() == "WARNING"
