"""配置模块单元测试"""

from pathlib import Path
from unittest.mock import patch


from modules.core.config import (
    AppConfig,
    ConfigManager,
    LogConfig,
    config_manager,
)


class TestLogConfig:
    """LogConfig 测试类"""

    def test_default_values(self):
        """测试默认值"""
        config = LogConfig()
        assert config.level == "INFO"
        assert config.log_dir == Path("logs")
        assert config.max_bytes == 10 * 1024 * 1024
        assert config.backup_count == 10
        assert config.retention_days == 7
        assert config.format == "json"

    def test_to_dict(self):
        """测试转换为字典"""
        config = LogConfig(level="DEBUG", max_bytes=1000)
        result = config.to_dict()
        
        assert result["level"] == "DEBUG"
        assert result["max_bytes"] == 1000
        assert result["log_dir"] == "logs"
        assert "backup_count" in result

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "level": "WARNING",
            "log_dir": "/var/log",
            "max_bytes": 2000,
            "backup_count": 5,
            "retention_days": 3,
            "format": "text",
        }
        config = LogConfig.from_dict(data)
        
        assert config.level == "WARNING"
        assert config.log_dir == Path("/var/log")
        assert config.max_bytes == 2000
        assert config.backup_count == 5
        assert config.retention_days == 3
        assert config.format == "text"

    def test_from_dict_partial(self):
        """测试从部分字典创建（使用默认值）"""
        data = {"level": "ERROR"}
        config = LogConfig.from_dict(data)
        
        assert config.level == "ERROR"
        assert config.max_bytes == 10 * 1024 * 1024  # 默认值


class TestAppConfig:
    """AppConfig 测试类"""

    def test_default_values(self):
        """测试默认值"""
        config = AppConfig()
        assert config.name == "mat-device-control"
        assert config.debug is False
        assert isinstance(config.log, LogConfig)

    def test_to_dict(self):
        """测试转换为字典"""
        config = AppConfig(
            name="test-app",
            debug=True,
            log=LogConfig(level="DEBUG"),
        )
        result = config.to_dict()
        
        assert result["app"]["name"] == "test-app"
        assert result["app"]["debug"] is True
        assert result["log"]["level"] == "DEBUG"

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "app": {"name": "my-app", "debug": True},
            "log": {"level": "CRITICAL", "max_bytes": 5000},
        }
        config = AppConfig.from_dict(data)
        
        assert config.name == "my-app"
        assert config.debug is True
        assert config.log.level == "CRITICAL"
        assert config.log.max_bytes == 5000


class TestConfigManager:
    """ConfigManager 测试类"""

    def test_singleton(self):
        """测试单例模式"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        
        assert manager1 is manager2

    def test_singleton_with_lock(self):
        """测试单例模式线程安全"""
        import threading
        
        instances = []
        
        def create_instance():
            instances.append(ConfigManager())
        
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有实例应该是同一个对象
        assert all(inst is instances[0] for inst in instances)

    def test_config_property(self):
        """测试配置属性访问"""
        config = config_manager.config
        assert isinstance(config, AppConfig)
        assert isinstance(config.log, LogConfig)

    def test_update_log_config(self, tmp_path):
        """测试更新日志配置"""
        # 使用临时配置文件
        with patch("modules.core.config.CONFIG_FILE", tmp_path / "test_config.toml"):
            manager = ConfigManager()
            manager._config = None  # 重置缓存
            
            manager.update_log_config(level="DEBUG", max_bytes=5000)
            
            assert manager.config.log.level == "DEBUG"
            assert manager.config.log.max_bytes == 5000

    def test_save_and_load_config(self, tmp_path):
        """测试保存和加载配置"""
        config_file = tmp_path / "test_config.toml"
        
        with patch("modules.core.config.CONFIG_FILE", config_file):
            manager = ConfigManager()
            manager._config = None  # 重置缓存
            
            # 更新并保存
            manager.update_log_config(level="WARNING", backup_count=15)
            manager.save_config()
            
            # 重置缓存并重新加载
            manager._config = None
            loaded_config = manager.config
            
            assert loaded_config.log.level == "WARNING"
            assert loaded_config.log.backup_count == 15
