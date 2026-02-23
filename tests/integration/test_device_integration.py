"""端到端集成测试

测试设备驱动框架的完整工作流程。
"""

import pytest
from unittest.mock import patch, MagicMock
from modules.device.factory import DriverFactory
from modules.device.base import DeviceConfig
from modules.device.enums import DeviceCategory, ConnectionType, ProtocolType


@pytest.fixture
def factory():
    """驱动工厂实例"""
    return DriverFactory()


@pytest.fixture
def e36312a_config():
    """E36312A配置"""
    return DeviceConfig(
        device_id="e36312a_001",
        model="E36312A",
        manufacturer="Keysight",
        category=DeviceCategory.POWER_SUPPLY,
        connection_type=ConnectionType.TCPIP,
        protocol=ProtocolType.SCPI,
        resource_string="TCPIP0::192.168.1.100::5025::SOCKET",
    )


@pytest.fixture
def sds1000x_config():
    """SDS1000X配置"""
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
async def test_e2e_keysight_power_supply_workflow(factory, e36312a_config):
    """端到端测试：Keysight电源完整工作流程"""
    # 1. 通过工厂创建驱动
    driver = factory.create_driver(e36312a_config)
    assert driver is not None
    assert driver._channel_count == 3

    # 2. Mock协议连接
    with (
        patch.object(driver.protocol, "connect", return_value=True),
        patch.object(
            driver.protocol, "query", return_value="Keysight,E36312A,SN12345,V1.0"
        ),
    ):
        # 连接设备
        result = await driver.connect()
        assert result is True
        assert driver.is_connected is True

        # 验证设备识别
        info = await driver.get_device_info()
        assert info.manufacturer == "Keysight"
        assert info.model == "E36312A"

    # 3. 测试电源操作
    with patch.object(driver.protocol, "write") as mock_write:
        # 设置电压
        await driver.set_voltage(1, 12.0)
        assert mock_write.called

        # 设置电流
        await driver.set_current(1, 2.5)

        # 启用输出
        await driver.enable_output(1)

    # 4. 测试测量操作
    with patch.object(
        driver.protocol, "query", side_effect=["+12.0", "+2.5", "+30.0", "1"]
    ):
        # 获取通道信息
        info = await driver.get_channel_info(1)
        assert info["voltage"] == 12.0
        assert info["current"] == 2.5
        assert info["power"] == 30.0
        assert info["output_enabled"] is True

    # 5. 断开连接
    with patch.object(driver.protocol, "disconnect"):
        await driver.disconnect()
        assert driver.is_connected is False


@pytest.mark.asyncio
async def test_e2e_siglent_oscilloscope_workflow(factory, sds1000x_config):
    """端到端测试：Siglent示波器完整工作流程"""
    # 1. 通过工厂创建驱动
    driver = factory.create_driver(sds1000x_config)
    assert driver is not None
    assert driver._channel_count == 4

    # 2. Mock协议连接
    with (
        patch.object(driver.protocol, "connect", return_value=True),
        patch.object(
            driver.protocol, "query", return_value="Siglent,SDS1104X-E,SN12345,V1.0"
        ),
    ):
        # 连接设备
        result = await driver.connect()
        assert result is True
        assert driver.is_connected is True

        # 验证设备识别
        info = await driver.get_device_info()
        assert info.manufacturer == "Siglent"
        assert info.model == "SDS1104X-E"

    # 3. 测试示波器操作
    with patch.object(driver.protocol, "write") as mock_write:
        # 启用通道
        await driver.enable_channel(1)

        # 设置通道刻度
        await driver.set_channel_scale(1, 0.5)

        # 设置时基
        await driver.set_timebase(1e-3)

        # 设置触发
        await driver.set_trigger_mode("EDGE")
        await driver.set_trigger_source("C1")
        await driver.set_trigger_level(2.5)

    # 4. 测试测量操作
    with patch.object(
        driver.protocol,
        "query",
        side_effect=[
            "C1:PAVA FREQ,1.0000E+03",  # frequency
            "C1:PAVA PKPK,5.0000E+00",  # peak-to-peak
            "C1:PAVA RMS,3.5350E+00",  # rms
        ],
    ):
        # 获取波形信息
        info = await driver.get_waveform_info(1)
        assert info["frequency"] == 1000.0
        assert info["peak_to_peak"] == 5.0
        assert info["rms"] == 3.535

    # 5. 测试采集控制
    with patch.object(driver.protocol, "write") as mock_write:
        await driver.start_acquisition()
        await driver.stop_acquisition()
        await driver.autoset()

    # 6. 断开连接
    with patch.object(driver.protocol, "disconnect"):
        await driver.disconnect()
        assert driver.is_connected is False


@pytest.mark.asyncio
async def test_e2e_multiple_devices_concurrent(
    factory, e36312a_config, sds1000x_config
):
    """端到端测试：多设备并发操作"""
    import asyncio

    # 创建两个设备
    power_supply = factory.create_driver(e36312a_config)
    oscilloscope = factory.create_driver(sds1000x_config)

    # 并发连接
    async def connect_device(device, idn_response):
        with (
            patch.object(device.protocol, "_connect_tcpip", return_value=True),
            patch.object(device.protocol, "query", return_value=idn_response),
        ):
            return await device.connect()

    results = await asyncio.gather(
        connect_device(power_supply, "Keysight,E36312A,SN12345,V1.0"),
        connect_device(oscilloscope, "Siglent,SDS1104X-E,SN67890,V2.0"),
    )

    # 验证两个设备都连接成功
    assert results[0] is True
    assert results[1] is True
    assert power_supply.is_connected is True
    assert oscilloscope.is_connected is True

    # 并发操作
    async def measure_power(device):
        with patch.object(device.protocol, "query", return_value="+30.5"):
            return await device.measure_power(1)

    async def measure_frequency(device):
        with patch.object(
            device.protocol, "query", return_value="C1:PAVA FREQ,1.0000E+03"
        ):
            return await device.measure_frequency(1)

    power, frequency = await asyncio.gather(
        measure_power(power_supply), measure_frequency(oscilloscope)
    )

    assert power == 30.5
    assert frequency == 1000.0


@pytest.mark.asyncio
async def test_e2e_error_handling(factory, e36312a_config):
    """端到端测试：错误处理"""
    from modules.device.base import DeviceConnectionError

    driver = factory.create_driver(e36312a_config)

    # 测试连接失败
    with patch.object(driver.protocol, "_connect_tcpip", return_value=False):
        with pytest.raises(DeviceConnectionError, match="Failed to connect"):
            await driver.connect()

    assert driver.is_connected is False

    # 测试未连接时的操作
    with pytest.raises(RuntimeError, match="Not connected"):
        await driver.set_voltage(1, 12.0)

    # 测试参数验证
    with (
        patch.object(driver.protocol, "_connect_tcpip", return_value=True),
        patch.object(
            driver.protocol, "query", return_value="Keysight,E36312A,SN12345,V1.0"
        ),
    ):
        await driver.connect()

    # 测试无效通道
    with pytest.raises(ValueError, match="Channel must be 1-3"):
        await driver.set_voltage(4, 12.0)

    # 测试超出范围的电压
    with pytest.raises(ValueError, match="voltage must be"):
        await driver.set_voltage(1, 100.0)


@pytest.mark.asyncio
async def test_e2e_device_lifecycle(factory, e36312a_config):
    """端到端测试：设备生命周期"""
    driver = factory.create_driver(e36312a_config)

    # 初始状态
    assert driver.is_connected is False

    # 连接
    with (
        patch.object(driver.protocol, "_connect_tcpip", return_value=True),
        patch.object(
            driver.protocol, "query", return_value="Keysight,E36312A,SN12345,V1.0"
        ),
    ):
        await driver.connect()
        assert driver.is_connected is True

    # 使用异步上下文管理器
    new_driver = factory.create_driver(e36312a_config)

    with (
        patch.object(new_driver.protocol, "_connect_tcpip", return_value=True),
        patch.object(new_driver.protocol, "disconnect"),
        patch.object(
            new_driver.protocol, "query", return_value="Keysight,E36312A,SN12345,V1.0"
        ),
    ):
        async with new_driver as device:
            assert device.is_connected is True
            # 在此执行操作...

        # 退出上下文后自动断开
        assert device.is_connected is False
