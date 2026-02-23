"""Tests for DeviceLoader"""

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock
import tempfile
import os
import tomli_w

from modules.device.loader import DeviceLoader, get_device_loader, reset_device_loader
from modules.device.enums import DeviceCategory


@pytest.fixture
def temp_config_content():
    """创建配置内容"""
    return {
        "devices": [
            {
                "device_id": "test_psu_001",
                "model": "E36312A",
                "manufacturer": "Keysight",
                "category": "power_supply",
                "connection_type": "tcpip",
                "protocol": "scpi",
                "resource_string": "TCPIP0::192.168.1.100::5025::SOCKET",
                "auto_connect": True,
                "enabled": True,
            },
            {
                "device_id": "test_scope_001",
                "model": "SDS1104X-E",
                "manufacturer": "Siglent",
                "category": "oscilloscope",
                "connection_type": "tcpip",
                "protocol": "scpi",
                "resource_string": "TCPIP0::192.168.1.101::5025::SOCKET",
                "auto_connect": False,
                "enabled": True,
            },
            {
                "device_id": "disabled_device",
                "model": "E36312A",
                "manufacturer": "Keysight",
                "category": "power_supply",
                "connection_type": "tcpip",
                "protocol": "scpi",
                "resource_string": "TCPIP0::192.168.1.200::5025::SOCKET",
                "auto_connect": True,
                "enabled": False,
            },
        ]
    }


@pytest.fixture
def temp_config_file(temp_config_content):
    """创建临时配置文件"""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
        tomli_w.dump(temp_config_content, f)
        temp_path = f.name

    yield temp_path

    # 清理
    try:
        os.unlink(temp_path)
    except:
        pass


@pytest.fixture
def loader(temp_config_file):
    """创建加载器实例"""
    reset_device_loader()
    reset_controller = __import__(
        "modules.device.controller", fromlist=["reset_controller"]
    )
    reset_controller.reset_controller()
    return DeviceLoader(temp_config_file)


class TestDeviceLoader:
    """设备加载器测试"""

    def test_load_config_success(self, loader, temp_config_content):
        """测试成功加载配置"""
        configs = loader.load_config()

        assert len(configs) == 3
        assert configs[0]["device_id"] == "test_psu_001"
        assert configs[1]["device_id"] == "test_scope_001"
        assert configs[2]["device_id"] == "disabled_device"

    def test_load_config_file_not_found(self):
        """测试配置文件不存在"""
        loader = DeviceLoader("nonexistent.toml")
        configs = loader.load_config()

        assert configs == []

    @pytest.mark.asyncio
    async def test_initialize_devices_creates_enabled(self, loader):
        """测试只创建启用的设备"""
        results = await loader.initialize_devices(auto_connect=False, only_enabled=True)

        # 2个启用的设备应该成功创建
        assert "test_psu_001" in results
        assert "test_scope_001" in results
        assert results["test_psu_001"]["success"] is True
        assert results["test_scope_001"]["success"] is True

        # 禁用的设备应该被跳过
        assert "disabled_device" in results
        assert results["disabled_device"]["success"] is False
        assert "disabled" in results["disabled_device"]["error"].lower()

    @pytest.mark.asyncio
    async def test_initialize_devices_creates_all(self, loader):
        """测试创建所有设备（包括禁用的）"""
        results = await loader.initialize_devices(
            auto_connect=False, only_enabled=False
        )

        # 所有3个设备都应该创建
        assert len(results) == 3
        assert all(r["success"] for r in results.values())

    @pytest.mark.asyncio
    async def test_shutdown_devices(self, loader):
        """测试关闭设备"""
        # 先初始化一些设备
        await loader.initialize_devices(auto_connect=False, only_enabled=True)

        # 然后关闭（不应该抛出异常）
        await loader.shutdown_devices()


class TestGlobalLoader:
    """全局加载器测试"""

    def test_get_device_loader_singleton(self, temp_config_file):
        """测试单例模式"""
        reset_device_loader()

        loader1 = get_device_loader(temp_config_file)
        loader2 = get_device_loader(temp_config_file)

        assert loader1 is loader2

    def test_reset_device_loader(self, temp_config_file):
        """测试重置加载器"""
        loader1 = get_device_loader(temp_config_file)
        reset_device_loader()
        loader2 = get_device_loader(temp_config_file)

        assert loader1 is not loader2
