"""Tests for Siglent SDS1000X oscilloscope driver"""

import pytest
from unittest.mock import patch
from modules.device.drivers.siglent.sds1000x import SiglentSDS1000X
from modules.device.base import DeviceConfig
from modules.device.enums import DeviceCategory, ConnectionType, ProtocolType


@pytest.fixture
def sds1000x_config():
    """SDS1000X测试配置"""
    return DeviceConfig(
        device_id="sds1104xe_001",
        model="SDS1104X-E",
        manufacturer="Siglent",
        category=DeviceCategory.OSCILLOSCOPE,
        connection_type=ConnectionType.TCPIP,
        protocol=ProtocolType.SCPI,
        resource_string="TCPIP0::192.168.1.101::5025::SOCKET",
    )


@pytest.mark.asyncio
async def test_sds1000x_creation(sds1000x_config):
    """测试SDS1000X驱动创建"""
    driver = SiglentSDS1000X(sds1000x_config)
    assert driver is not None
    assert driver.config == sds1000x_config
    assert driver._channel_count == 4


@pytest.mark.asyncio
async def test_sds1000x_enable_channel(sds1000x_config):
    """测试启用通道"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.enable_channel(1)
        mock_write.assert_called_once_with("C1:TRACE ON")


@pytest.mark.asyncio
async def test_sds1000x_disable_channel(sds1000x_config):
    """测试禁用通道"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.disable_channel(1)
        mock_write.assert_called_once_with("C1:TRACE OFF")


@pytest.mark.asyncio
async def test_sds1000x_set_channel_scale(sds1000x_config):
    """测试设置通道刻度"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.set_channel_scale(1, 0.5)  # 0.5V/div
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert "C1:VDIV" in call_args
        assert "0.5" in call_args


@pytest.mark.asyncio
async def test_sds1000x_set_timebase(sds1000x_config):
    """测试设置时基"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.set_timebase(1e-3)  # 1ms/div
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert "TIME_DIV" in call_args
        assert "0.001" in call_args


@pytest.mark.asyncio
async def test_sds1000x_measure_frequency(sds1000x_config):
    """测试频率测量"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(
        driver.protocol, "query", return_value="C1:PAVA FREQ,1.0000E+03"
    ) as mock_query:
        freq = await driver.measure_frequency(1)

        mock_query.assert_called_once_with("C1:PAVA? FREQ")
        assert freq == 1000.0


@pytest.mark.asyncio
async def test_sds1000x_measure_period(sds1000x_config):
    """测试周期测量"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(
        driver.protocol, "query", return_value="C1:PAVA PERI,1.0000E-03"
    ) as mock_query:
        period = await driver.measure_period(1)

        mock_query.assert_called_once_with("C1:PAVA? PERI")
        assert period == 1e-3


@pytest.mark.asyncio
async def test_sds1000x_measure_peak_to_peak(sds1000x_config):
    """测试峰峰值测量"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(
        driver.protocol, "query", return_value="C1:PAVA PKPK,5.0000E+00"
    ) as mock_query:
        vpp = await driver.measure_peak_to_peak(1)

        mock_query.assert_called_once_with("C1:PAVA? PKPK")
        assert vpp == 5.0


@pytest.mark.asyncio
async def test_sds1000x_measure_rms(sds1000x_config):
    """测试有效值测量"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(
        driver.protocol, "query", return_value="C1:PAVA RMS,3.5350E+00"
    ) as mock_query:
        vrms = await driver.measure_rms(1)

        mock_query.assert_called_once_with("C1:PAVA? RMS")
        assert vrms == 3.535


@pytest.mark.asyncio
async def test_sds1000x_set_trigger_mode(sds1000x_config):
    """测试设置触发模式"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.set_trigger_mode("EDGE")
        mock_write.assert_called_once_with("TRIG_MODE EDGE")


@pytest.mark.asyncio
async def test_sds1000x_set_trigger_source(sds1000x_config):
    """测试设置触发源"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.set_trigger_source("C1")
        mock_write.assert_called_once_with("TRIG_SRC C1")


@pytest.mark.asyncio
async def test_sds1000x_set_trigger_level(sds1000x_config):
    """测试设置触发电平"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.set_trigger_level(2.5)
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert "TRIG_LVL" in call_args
        assert "2.5" in call_args


@pytest.mark.asyncio
async def test_sds1000x_start_acquisition(sds1000x_config):
    """测试开始采集"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.start_acquisition()
        mock_write.assert_called_once_with("RUN")


@pytest.mark.asyncio
async def test_sds1000x_stop_acquisition(sds1000x_config):
    """测试停止采集"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.stop_acquisition()
        mock_write.assert_called_once_with("STOP")


@pytest.mark.asyncio
async def test_sds1000x_autoset(sds1000x_config):
    """测试自动设置"""
    driver = SiglentSDS1000X(sds1000x_config)

    with patch.object(driver.protocol, "write") as mock_write:
        await driver.autoset()
        mock_write.assert_called_once_with("AUTO")


@pytest.mark.asyncio
async def test_sds1000x_get_waveform_info(sds1000x_config):
    """测试获取波形信息"""
    driver = SiglentSDS1000X(sds1000x_config)

    # Mock协议查询
    with patch.object(
        driver.protocol,
        "query",
        side_effect=[
            "C1:PAVA FREQ,1.0000E+03",  # frequency
            "C1:PAVA PKPK,5.0000E+00",  # peak-to-peak
            "C1:PAVA RMS,3.5350E+00",  # rms
        ],
    ):
        info = await driver.get_waveform_info(1)

        assert info["channel"] == 1
        assert info["frequency"] == 1000.0
        assert info["peak_to_peak"] == 5.0
        assert info["rms"] == 3.535


@pytest.mark.asyncio
async def test_sds1000x_invalid_channel(sds1000x_config):
    """测试无效通道号"""
    driver = SiglentSDS1000X(sds1000x_config)

    with pytest.raises(ValueError, match="Channel must be 1-4"):
        await driver.enable_channel(5)
