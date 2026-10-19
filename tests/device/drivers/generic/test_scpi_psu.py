"""Tests for the generic SCPI power-supply driver (ATEStudio generic contract)."""

from unittest.mock import patch

import pytest
from modules.device.base import DeviceConfig
from modules.device.drivers.generic.scpi_psu import GenericSCPIPowerSupply
from modules.device.enums import ConnectionType, DeviceCategory, ProtocolType


@pytest.fixture
def psu_config() -> DeviceConfig:
    """通用电源测试配置。"""
    return DeviceConfig(
        device_id="psu001",
        model="GenericPSU",
        manufacturer="MAT",
        category=DeviceCategory.POWER_SUPPLY,
        connection_type=ConnectionType.TCPIP,
        protocol=ProtocolType.SCPI,
        resource_string="TCPIP0::127.0.0.1::5025::SOCKET",
    )


def test_generic_psu_creation(psu_config: DeviceConfig) -> None:
    """驱动创建且通道数为 1。"""
    driver = GenericSCPIPowerSupply(psu_config)
    assert driver._channel_count == 1
    assert driver.config == psu_config


@pytest.mark.asyncio
async def test_set_voltage_writes_scpi(psu_config: DeviceConfig) -> None:
    """set_voltage(value) 翻译为 SOURce1:VOLTage 命令。"""
    driver = GenericSCPIPowerSupply(psu_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.set_voltage(value=12.5)

    mock_write.assert_called_once()
    assert mock_write.call_args[0][0] == "SOURce1:VOLTage 12.500"


@pytest.mark.asyncio
async def test_set_voltage_channel_optional(psu_config: DeviceConfig) -> None:
    """显式通道号写入对应通道前缀。"""
    driver = GenericSCPIPowerSupply(psu_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.set_voltage(value=5.0, channel=2)

    assert mock_write.call_args[0][0] == "SOURce2:VOLTage 5.000"


@pytest.mark.asyncio
async def test_measure_voltage_parses_float(psu_config: DeviceConfig) -> None:
    """measure_voltage() 解析 SCPI 响应为浮点。"""
    driver = GenericSCPIPowerSupply(psu_config)

    with patch.object(driver.protocol, "query", return_value="12.500000") as mock_query:
        voltage = await driver.measure_voltage()

    assert voltage == pytest.approx(12.5)
    assert mock_query.call_args[0][0] == "MEASure1:VOLTage?"


@pytest.mark.asyncio
async def test_measure_current_parses_float(psu_config: DeviceConfig) -> None:
    """measure_current() 解析 SCPI 响应为浮点。"""
    driver = GenericSCPIPowerSupply(psu_config)

    with patch.object(driver.protocol, "query", return_value="0.100000"):
        current = await driver.measure_current()

    assert current == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_invalid_channel_raises(psu_config: DeviceConfig) -> None:
    """非法通道号抛 ValueError。"""
    driver = GenericSCPIPowerSupply(psu_config)

    with pytest.raises(ValueError, match="Channel must be"):
        await driver.set_voltage(value=1.0, channel=0)


@pytest.mark.asyncio
async def test_negative_voltage_raises(psu_config: DeviceConfig) -> None:
    """负电压抛 ValueError（fail-fast，不静默）。"""
    driver = GenericSCPIPowerSupply(psu_config)

    with pytest.raises(ValueError, match="Voltage must be"):
        await driver.set_voltage(value=-1.0)
