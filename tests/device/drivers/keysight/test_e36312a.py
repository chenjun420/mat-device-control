"""Tests for Keysight E36312A power supply driver"""

import pytest
from unittest.mock import patch
from modules.device.drivers.keysight.e36312a import KeysightE36312A
from modules.device.base import DeviceConfig
from modules.device.enums import DeviceCategory, ConnectionType, ProtocolType


@pytest.fixture
def e36312a_config():
    """E36312A测试配置"""
    return DeviceConfig(
        device_id="e36312a_001",
        model="E36312A",
        manufacturer="Keysight",
        category=DeviceCategory.POWER_SUPPLY,
        connection_type=ConnectionType.TCPIP,
        protocol=ProtocolType.SCPI,
        resource_string="TCPIP0::192.168.1.100::5025::SOCKET",
    )


@pytest.mark.asyncio
async def test_e36312a_creation(e36312a_config):
    """测试E36312A驱动创建"""
    driver = KeysightE36312A(e36312a_config)
    assert driver is not None
    assert driver.config == e36312a_config
    assert driver._channel_count == 3


@pytest.mark.asyncio
async def test_e36312a_set_voltage(e36312a_config):
    """测试设置电压"""
    driver = KeysightE36312A(e36312a_config)

    # Mock协议写入
    with patch.object(driver.protocol, "write") as mock_write:
        await driver.set_voltage(1, 12.0)
        mock_write.assert_called_once()
        # 验证SCPI命令格式
        call_args = mock_write.call_args[0][0]
        assert "SOURCE1:VOLTAGE" in call_args
        assert "12" in call_args


@pytest.mark.asyncio
async def test_e36312a_set_voltage_invalid_channel(e36312a_config):
    """测试设置电压（无效通道）"""
    driver = KeysightE36312A(e36312a_config)

    with pytest.raises(ValueError, match="Channel must be 1-3"):
        await driver.set_voltage(4, 12.0)


@pytest.mark.asyncio
async def test_e36312a_set_voltage_out_of_range(e36312a_config):
    """测试设置电压（超出范围）"""
    driver = KeysightE36312A(e36312a_config)

    with pytest.raises(ValueError, match="voltage must be"):
        await driver.set_voltage(1, 100.0)  # 通道1最大30V


@pytest.mark.asyncio
async def test_e36312a_set_current(e36312a_config):
    """测试设置电流"""
    driver = KeysightE36312A(e36312a_config)

    # Mock协议写入
    with patch.object(driver.protocol, "write") as mock_write:
        await driver.set_current(1, 2.5)
        mock_write.assert_called_once()
        # 验证SCPI命令格式
        call_args = mock_write.call_args[0][0]
        assert "SOURCE1:CURRENT" in call_args
        assert "2.5" in call_args


@pytest.mark.asyncio
async def test_e36312a_enable_output(e36312a_config):
    """测试启用输出"""
    driver = KeysightE36312A(e36312a_config)

    # Mock协议写入
    with patch.object(driver.protocol, "write") as mock_write:
        await driver.enable_output(1)
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert "OUTPUT1:STATE ON" in call_args


@pytest.mark.asyncio
async def test_e36312a_disable_output(e36312a_config):
    """测试禁用输出"""
    driver = KeysightE36312A(e36312a_config)

    # Mock协议写入
    with patch.object(driver.protocol, "write") as mock_write:
        await driver.disable_output(1)
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert "OUTPUT1:STATE OFF" in call_args


@pytest.mark.asyncio
async def test_e36312a_measure_voltage(e36312a_config):
    """测试测量电压"""
    driver = KeysightE36312A(e36312a_config)

    # Mock协议查询
    with patch.object(driver.protocol, "query", return_value="+12.345") as mock_query:
        voltage = await driver.measure_voltage(1)

        mock_query.assert_called_once()
        assert voltage == 12.345


@pytest.mark.asyncio
async def test_e36312a_measure_current(e36312a_config):
    """测试测量电流"""
    driver = KeysightE36312A(e36312a_config)

    # Mock协议查询
    with patch.object(driver.protocol, "query", return_value="+2.500") as mock_query:
        current = await driver.measure_current(1)

        mock_query.assert_called_once()
        assert current == 2.500


@pytest.mark.asyncio
async def test_e36312a_measure_power(e36312a_config):
    """测试测量功率"""
    driver = KeysightE36312A(e36312a_config)

    # Mock协议查询
    with patch.object(driver.protocol, "query", return_value="+30.862") as mock_query:
        power = await driver.measure_power(1)

        mock_query.assert_called_once()
        assert power == 30.862


@pytest.mark.asyncio
async def test_e36312a_get_output_state(e36312a_config):
    """测试获取输出状态"""
    driver = KeysightE36312A(e36312a_config)

    # Mock协议查询 - 输出启用
    with patch.object(driver.protocol, "query", return_value="1"):
        state = await driver.get_output_state(1)
        assert state is True

    # Mock协议查询 - 输出禁用
    with patch.object(driver.protocol, "query", return_value="0"):
        state = await driver.get_output_state(1)
        assert state is False


@pytest.mark.asyncio
async def test_e36312a_get_channel_info(e36312a_config):
    """测试获取通道信息"""
    driver = KeysightE36312A(e36312a_config)

    # Mock协议查询
    with patch.object(
        driver.protocol, "query", side_effect=["+12.0", "+2.5", "+30.0", "1"]
    ):
        info = await driver.get_channel_info(1)

        assert info["channel"] == 1
        assert info["voltage"] == 12.0
        assert info["current"] == 2.5
        assert info["power"] == 30.0
        assert info["output_enabled"] is True
        assert info["max_voltage"] == 30.0
        assert info["max_current"] == 5.0
        assert info["max_power"] == 80.0


@pytest.mark.asyncio
async def test_e36312a_channel_specs(e36312a_config):
    """测试通道规格"""
    driver = KeysightE36312A(e36312a_config)

    # 验证通道1和2规格 (30V, 5A, 80W)
    assert driver._max_voltage[0] == 30.0
    assert driver._max_current[0] == 5.0
    assert driver._max_power[0] == 80.0

    assert driver._max_voltage[1] == 30.0
    assert driver._max_current[1] == 5.0
    assert driver._max_power[1] == 80.0

    # 验证通道3规格 (5V, 3A, 15W)
    assert driver._max_voltage[2] == 5.0
    assert driver._max_current[2] == 3.0
    assert driver._max_power[2] == 15.0
