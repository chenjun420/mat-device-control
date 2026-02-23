"""Tests for device driver factory"""

import pytest
from modules.device.factory import DriverFactory, get_factory, reset_factory
from modules.device.base import DeviceConfig
from modules.device.enums import DeviceCategory, ConnectionType, ProtocolType


@pytest.fixture
def factory():
    """驱动工厂实例"""
    reset_factory()  # 确保每次测试都是全新状态
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


def test_factory_creation(factory):
    """测试工厂创建"""
    assert factory is not None


def test_get_factory_lazy_init():
    """测试全局工厂延迟初始化"""
    reset_factory()
    factory1 = get_factory()
    factory2 = get_factory()
    assert factory1 is factory2  # 同一个实例


def test_factory_create_keysight_power_supply(factory, e36312a_config):
    """测试创建Keysight电源驱动"""
    driver = factory.create_driver(e36312a_config)

    assert driver is not None
    assert driver.config == e36312a_config
    assert driver._channel_count == 3


def test_factory_create_siglent_oscilloscope(factory, sds1000x_config):
    """测试创建Siglent示波器驱动"""
    driver = factory.create_driver(sds1000x_config)

    assert driver is not None
    assert driver.config == sds1000x_config
    assert driver._channel_count == 4


def test_factory_unsupported_device(factory):
    """测试创建不支持的设备"""
    config = DeviceConfig(
        device_id="unknown_001",
        model="UNKNOWN_MODEL",
        manufacturer="Unknown",
        category=DeviceCategory.GENERIC,
        connection_type=ConnectionType.TCPIP,
        protocol=ProtocolType.SCPI,
        resource_string="TCPIP0::192.168.1.200::5025::SOCKET",
    )

    with pytest.raises(ValueError, match="Unsupported device"):
        factory.create_driver(config)


def test_factory_get_supported_devices(factory):
    """测试获取支持的设备列表"""
    supported = factory.get_supported_devices()

    assert isinstance(supported, list)
    assert len(supported) > 0
    assert "Keysight.E36312A" in supported
    assert "Siglent.SDS1000X-E" in supported


def test_factory_is_device_supported(factory, e36312a_config):
    """测试检查设备是否支持"""
    assert factory.is_device_supported(e36312a_config) is True

    unsupported_config = DeviceConfig(
        device_id="unknown_001",
        model="UNKNOWN_MODEL",
        manufacturer="Unknown",
        category=DeviceCategory.GENERIC,
        connection_type=ConnectionType.TCPIP,
        protocol=ProtocolType.SCPI,
        resource_string="TCPIP0::192.168.1.200::5025::SOCKET",
    )

    assert factory.is_device_supported(unsupported_config) is False


def test_factory_driver_caching(factory, e36312a_config):
    """测试驱动类缓存机制"""
    # 创建第一个驱动
    driver1 = factory.create_driver(e36312a_config)

    # 检查已加载驱动
    loaded = factory.get_loaded_drivers()
    assert "Keysight.E36312A" in loaded

    # 创建第二个同类型驱动（应该使用缓存）
    driver2 = factory.create_driver(e36312a_config)

    # 验证类型相同
    assert type(driver1) is type(driver2)


def test_factory_get_memory_usage(factory, e36312a_config):
    """测试获取内存使用统计"""
    # 初始状态
    usage = factory.get_memory_usage()
    assert usage["registered_drivers"] > 0
    assert usage["loaded_drivers"] == 0
    assert usage["loaded_modules"] == 0

    # 创建驱动后
    factory.create_driver(e36312a_config)
    usage = factory.get_memory_usage()
    assert usage["loaded_drivers"] == 1
    assert usage["loaded_modules"] >= 1


def test_factory_clear_cache(factory, e36312a_config):
    """测试清除缓存"""
    # 创建驱动
    factory.create_driver(e36312a_config)
    assert len(factory.get_loaded_drivers()) == 1

    # 清除缓存
    factory.clear_cache()
    assert len(factory.get_loaded_drivers()) == 0


def test_factory_register_unregister(factory):
    """测试注册和注销驱动"""
    # 注册新驱动
    factory.register_driver("Test", "Model1", "some.module:DriverClass")
    assert factory.is_device_supported(
        DeviceConfig(
            device_id="test",
            model="Model1",
            manufacturer="Test",
            category=DeviceCategory.GENERIC,
            connection_type=ConnectionType.TCPIP,
            protocol=ProtocolType.SCPI,
            resource_string="TCPIP0::test::INSTR",
        )
    )

    # 注销驱动
    result = factory.unregister_driver("Test", "Model1")
    assert result is True
    assert not factory.is_device_supported(
        DeviceConfig(
            device_id="test",
            model="Model1",
            manufacturer="Test",
            category=DeviceCategory.GENERIC,
            connection_type=ConnectionType.TCPIP,
            protocol=ProtocolType.SCPI,
            resource_string="TCPIP0::test::INSTR",
        )
    )

    # 注销不存在的驱动
    result = factory.unregister_driver("Unknown", "Unknown")
    assert result is False
