"""设备注册表单元测试"""

import pytest

from modules.device.base import BaseDriver, DeviceConfig
from modules.device.enums import (
    ConnectionType,
    DeviceCategory,
    DeviceState,
    ProtocolType,
)


class MockDriver(BaseDriver):
    """用于测试的模拟驱动"""

    driver_name = "mock_driver"

    async def _connect_impl(self) -> bool:
        return True

    async def _disconnect_impl(self) -> None:
        pass

    async def _write_impl(self, command: str) -> None:
        pass

    async def _query_impl(self, command: str) -> str:
        return "OK"

    async def _read_impl(self) -> str:
        return "OK"


class AnotherMockDriver(BaseDriver):
    """另一个用于测试的模拟驱动"""

    driver_name = "another_mock_driver"

    async def _connect_impl(self) -> bool:
        return True

    async def _disconnect_impl(self) -> None:
        pass

    async def _write_impl(self, command: str) -> None:
        pass

    async def _query_impl(self, command: str) -> str:
        return "OK"

    async def _read_impl(self) -> str:
        return "OK"


class TestDriverRegistrySingleton:
    """DriverRegistry 单例模式测试"""

    def test_singleton_instance(self):
        """测试单例模式 - 同一实例"""
        from modules.device.registry import DriverRegistry

        registry1 = DriverRegistry()
        registry2 = DriverRegistry()

        assert registry1 is registry2

    def test_singleton_get_instance(self):
        """测试单例模式 - get_instance 方法"""
        from modules.device.registry import DriverRegistry

        registry1 = DriverRegistry.get_instance()
        registry2 = DriverRegistry.get_instance()

        assert registry1 is registry2

    def test_clear_instance(self):
        """测试清除单例实例"""
        from modules.device.registry import DriverRegistry

        registry1 = DriverRegistry()
        DriverRegistry._clear_instance()
        registry2 = DriverRegistry()

        # 清除后应该是新实例
        assert registry1 is not registry2


class TestDriverRegistration:
    """驱动注册测试"""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """每个测试前清除注册表"""
        from modules.device.registry import DriverRegistry

        DriverRegistry._clear_instance()
        yield
        DriverRegistry._clear_instance()

    def test_register_driver(self):
        """测试注册驱动"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )

        # 验证驱动已注册
        driver_class = registry.get_driver(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )
        assert driver_class is MockDriver

    def test_register_multiple_drivers(self):
        """测试注册多个驱动"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="ModelA",
        )
        registry.register_driver(
            driver_class=AnotherMockDriver,
            category=DeviceCategory.ELECTRONIC_LOAD,
            manufacturer="TestManufacturer",
            model="ModelB",
        )

        driver_a = registry.get_driver(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="ModelA",
        )
        driver_b = registry.get_driver(
            category=DeviceCategory.ELECTRONIC_LOAD,
            manufacturer="TestManufacturer",
            model="ModelB",
        )

        assert driver_a is MockDriver
        assert driver_b is AnotherMockDriver

    def test_register_driver_decorator(self):
        """测试使用装饰器注册驱动"""
        from modules.device.registry import DriverRegistry, register_driver

        @register_driver(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="DecoratorTest",
            model="DecoratedModel",
        )
        class DecoratedDriver(BaseDriver):
            driver_name = "decorated_driver"

            async def _connect_impl(self) -> bool:
                return True

            async def _disconnect_impl(self) -> None:
                pass

            async def _write_impl(self, command: str) -> None:
                pass

            async def _query_impl(self, command: str) -> str:
                return "OK"

            async def _read_impl(self) -> str:
                return "OK"

        registry = DriverRegistry()
        driver_class = registry.get_driver(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="DecoratorTest",
            model="DecoratedModel",
        )

        assert driver_class is DecoratedDriver

    def test_register_duplicate_driver(self):
        """测试注册重复驱动（应覆盖）"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )
        # 注册相同键的驱动应覆盖
        registry.register_driver(
            driver_class=AnotherMockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )

        driver_class = registry.get_driver(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )
        assert driver_class is AnotherMockDriver


class TestDriverDiscovery:
    """驱动发现测试"""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """每个测试前清除注册表"""
        from modules.device.registry import DriverRegistry

        DriverRegistry._clear_instance()
        yield
        DriverRegistry._clear_instance()

    def test_get_driver_by_category(self):
        """测试按类别获取驱动"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )
        registry.register_driver(
            driver_class=AnotherMockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36313A",
        )

        drivers = registry.get_drivers_by_category(DeviceCategory.POWER_SUPPLY)

        assert len(drivers) == 2
        assert MockDriver in drivers
        assert AnotherMockDriver in drivers

    def test_get_driver_by_manufacturer(self):
        """测试按制造商获取驱动"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )
        registry.register_driver(
            driver_class=AnotherMockDriver,
            category=DeviceCategory.ELECTRONIC_LOAD,
            manufacturer="Keysight",
            model="EL30000",
        )

        drivers = registry.get_drivers_by_manufacturer("Keysight")

        assert len(drivers) == 2
        assert MockDriver in drivers
        assert AnotherMockDriver in drivers

    def test_get_driver_not_found(self):
        """测试获取不存在的驱动"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        driver_class = registry.get_driver(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="NonExistent",
            model="Unknown",
        )

        assert driver_class is None

    def test_get_all_drivers(self):
        """测试获取所有已注册驱动"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )
        registry.register_driver(
            driver_class=AnotherMockDriver,
            category=DeviceCategory.ELECTRONIC_LOAD,
            manufacturer="ITECH",
            model="IT8512A",
        )

        all_drivers = registry.get_all_drivers()

        assert len(all_drivers) == 2
        assert MockDriver in all_drivers
        assert AnotherMockDriver in all_drivers

    def test_get_driver_info(self):
        """测试获取驱动信息"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )

        info = registry.get_driver_info(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )

        assert info is not None
        assert info["category"] == DeviceCategory.POWER_SUPPLY
        assert info["manufacturer"] == "Keysight"
        assert info["model"] == "E36312A"
        assert info["driver_class"] is MockDriver


class TestDriverRegistryUtilities:
    """驱动注册表工具方法测试"""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """每个测试前清除注册表"""
        from modules.device.registry import DriverRegistry

        DriverRegistry._clear_instance()
        yield
        DriverRegistry._clear_instance()

    def test_unregister_driver(self):
        """测试注销驱动"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )

        # 注销驱动
        result = registry.unregister_driver(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )

        assert result is True

        # 验证驱动已注销
        driver_class = registry.get_driver(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )
        assert driver_class is None

    def test_unregister_nonexistent_driver(self):
        """测试注销不存在的驱动"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        result = registry.unregister_driver(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="NonExistent",
            model="Unknown",
        )

        assert result is False

    def test_clear_all_drivers(self):
        """测试清除所有驱动"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )
        registry.register_driver(
            driver_class=AnotherMockDriver,
            category=DeviceCategory.ELECTRONIC_LOAD,
            manufacturer="ITECH",
            model="IT8512A",
        )

        registry.clear()

        all_drivers = registry.get_all_drivers()
        assert len(all_drivers) == 0

    def test_driver_count(self):
        """测试驱动计数"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        assert registry.count() == 0

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )

        assert registry.count() == 1

        registry.register_driver(
            driver_class=AnotherMockDriver,
            category=DeviceCategory.ELECTRONIC_LOAD,
            manufacturer="ITECH",
            model="IT8512A",
        )

        assert registry.count() == 2


class TestDriverRegistryValidation:
    """驱动注册表验证测试"""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """每个测试前清除注册表"""
        from modules.device.registry import DriverRegistry

        DriverRegistry._clear_instance()
        yield
        DriverRegistry._clear_instance()

    def test_register_invalid_driver_class(self):
        """测试注册无效驱动类"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        with pytest.raises(TypeError):
            registry.register_driver(
                driver_class=object,  # type: ignore
                category=DeviceCategory.POWER_SUPPLY,
                manufacturer="Test",
                model="Test",
            )

    def test_register_none_driver_class(self):
        """测试注册 None 驱动类"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        with pytest.raises(TypeError):
            registry.register_driver(
                driver_class=None,  # type: ignore
                category=DeviceCategory.POWER_SUPPLY,
                manufacturer="Test",
                model="Test",
            )

    def test_is_driver_registered(self):
        """测试检查驱动是否已注册"""
        from modules.device.registry import DriverRegistry

        registry = DriverRegistry()

        assert not registry.is_registered(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )

        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )

        assert registry.is_registered(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )
