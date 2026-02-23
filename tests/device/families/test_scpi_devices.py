"""Tests for SCPI device family"""

import pytest
from unittest.mock import patch, MagicMock
from modules.device.families.scpi_devices import SCPIDevice
from modules.device.base import DeviceConfig
from modules.device.enums import DeviceCategory, ConnectionType, ProtocolType


@pytest.fixture
def device_config():
    """测试设备配置"""
    return DeviceConfig(
        device_id="test_device",
        model="TEST_MODEL",
        manufacturer="TEST_MANUFACTURER",
        category=DeviceCategory.GENERIC,
        connection_type=ConnectionType.TCPIP,
        protocol=ProtocolType.SCPI,
        resource_string="TCPIP0::192.168.1.100::5025::SOCKET",
    )


@pytest.mark.asyncio
async def test_scpi_device_creation(device_config):
    """测试SCPI设备创建"""
    device = SCPIDevice(device_config)
    assert device is not None
    assert device.config == device_config


@pytest.mark.asyncio
async def test_scpi_device_identify(device_config):
    """测试设备识别"""
    device = SCPIDevice(device_config)

    # Mock协议查询
    with patch.object(
        device.protocol,
        "query",
        return_value="TEST_MANUFACTURER,TEST_MODEL,SN12345,V1.0",
    ):
        await device._identify_device()

        assert device._manufacturer == "TEST_MANUFACTURER"
        assert device._model == "TEST_MODEL"
        assert device._serial_number == "SN12345"
        assert device._firmware_version == "V1.0"


@pytest.mark.asyncio
async def test_scpi_device_reset(device_config):
    """测试设备复位"""
    device = SCPIDevice(device_config)

    with patch.object(device.protocol, "write") as mock_write:
        await device.reset()
        mock_write.assert_called_once_with("*RST")


@pytest.mark.asyncio
async def test_scpi_device_wait_for_operation_complete(device_config):
    """测试等待操作完成"""
    device = SCPIDevice(device_config)

    with patch.object(device.protocol, "query", return_value="1") as mock_query:
        await device.wait_for_operation_complete()
        mock_query.assert_called_once_with("*OPC?")


@pytest.mark.asyncio
async def test_scpi_device_get_error_no_error(device_config):
    """测试获取错误信息（无错误）"""
    device = SCPIDevice(device_config)

    with patch.object(device.protocol, "query", return_value='+0,"No error"'):
        error = await device.get_error()
        assert error is None


@pytest.mark.asyncio
async def test_scpi_device_get_error_with_error(device_config):
    """测试获取错误信息（有错误）"""
    device = SCPIDevice(device_config)

    with patch.object(device.protocol, "query", return_value='+123,"Error message"'):
        error = await device.get_error()
        assert error == '+123,"Error message"'


@pytest.mark.asyncio
async def test_scpi_device_clear_status(device_config):
    """测试清除状态寄存器"""
    device = SCPIDevice(device_config)

    with patch.object(device.protocol, "write") as mock_write:
        await device.clear_status()
        mock_write.assert_called_once_with("*CLS")


@pytest.mark.asyncio
async def test_scpi_device_get_device_info(device_config):
    """测试获取设备信息"""
    device = SCPIDevice(device_config)

    # 设置识别信息
    device._manufacturer = "Keysight"
    device._model = "E36312A"
    device._serial_number = "SN12345"
    device._firmware_version = "V1.0"

    info = await device.get_device_info()

    assert info.device_id == "test_device"
    assert info.manufacturer == "Keysight"
    assert info.model == "E36312A"
    assert info.serial_number == "SN12345"
    assert info.firmware_version == "V1.0"


@pytest.mark.asyncio
async def test_scpi_device_connect_success(device_config):
    """测试SCPI设备连接成功"""
    device = SCPIDevice(device_config)

    # Mock协议连接
    with (
        patch.object(device.protocol, "connect", return_value=True),
        patch.object(
            device.protocol, "query", return_value="Keysight,E36312A,SN12345,V1.0"
        ),
    ):
        result = await device._connect_impl()

        assert result is True
