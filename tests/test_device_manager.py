"""设备管理器单元测试"""

import pytest

from modules.device.base import BaseDriver, DeviceConfig, DeviceConnectionError
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


class TestDeviceManagerSingleton:
    """DeviceManager 单例模式测试"""

    def test_singleton_instance(self):
        """测试单例模式 - 同一实例"""
        from modules.device.manager import DeviceManager

        manager1 = DeviceManager()
        manager2 = DeviceManager()

        assert manager1 is manager2

    def test_singleton_get_instance(self):
        """测试单例模式 - get_instance 方法"""
        from modules.device.manager import DeviceManager

        manager1 = DeviceManager.get_instance()
        manager2 = DeviceManager.get_instance()

        assert manager1 is manager2

    def test_clear_instance(self):
        """测试清除单例实例"""
        from modules.device.manager import DeviceManager

        manager1 = DeviceManager()
        DeviceManager._clear_instance()
        manager2 = DeviceManager()

        # 清除后应该是新实例
        assert manager1 is not manager2


class TestDeviceLifecycle:
    """设备生命周期管理测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清除管理器和注册表"""
        from modules.device.manager import DeviceManager
        from modules.device.registry import DriverRegistry

        DeviceManager._clear_instance()
        DriverRegistry._clear_instance()

        # 注册测试驱动
        registry = DriverRegistry()
        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )

        yield

        DeviceManager._clear_instance()
        DriverRegistry._clear_instance()

    @pytest.fixture
    def device_config(self) -> DeviceConfig:
        """创建测试设备配置"""
        return DeviceConfig(
            device_id="PSU001",
            model="TestModel",
            manufacturer="TestManufacturer",
            category=DeviceCategory.POWER_SUPPLY,
            connection_type=ConnectionType.TCPIP,
            protocol=ProtocolType.VISA,
            resource_string="TCPIP0::192.168.1.100::inst0::INSTR",
        )

    @pytest.mark.asyncio
    async def test_create_device(self, device_config):
        """测试创建设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()
        driver = await manager.create_device(device_config)

        assert driver is not None
        assert driver.config.device_id == "PSU001"
        assert driver.state == DeviceState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_create_device_already_exists(self, device_config):
        """测试创建已存在的设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()
        await manager.create_device(device_config)

        with pytest.raises(ValueError, match="already exists"):
            await manager.create_device(device_config)

    @pytest.mark.asyncio
    async def test_remove_device(self, device_config):
        """测试移除设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()
        await manager.create_device(device_config)

        result = await manager.remove_device("PSU001")

        assert result is True
        assert manager.get_device("PSU001") is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_device(self):
        """测试移除不存在的设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()

        result = await manager.remove_device("NONEXISTENT")

        assert result is False

    @pytest.mark.asyncio
    async def test_connect_device(self, device_config):
        """测试连接设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()
        await manager.create_device(device_config)

        result = await manager.connect_device("PSU001")

        assert result is True
        driver = manager.get_device("PSU001")
        assert driver is not None
        assert driver.state == DeviceState.CONNECTED

    @pytest.mark.asyncio
    async def test_connect_nonexistent_device(self):
        """测试连接不存在的设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()

        with pytest.raises(KeyError):
            await manager.connect_device("NONEXISTENT")

    @pytest.mark.asyncio
    async def test_disconnect_device(self, device_config):
        """测试断开设备连接"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()
        await manager.create_device(device_config)
        await manager.connect_device("PSU001")

        await manager.disconnect_device("PSU001")

        driver = manager.get_device("PSU001")
        assert driver is not None
        assert driver.state == DeviceState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_device(self):
        """测试断开不存在的设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()

        # 不应抛出异常
        await manager.disconnect_device("NONEXISTENT")


class TestDeviceQueries:
    """设备查询测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清除管理器和注册表"""
        from modules.device.manager import DeviceManager
        from modules.device.registry import DriverRegistry

        DeviceManager._clear_instance()
        DriverRegistry._clear_instance()

        # 注册测试驱动
        registry = DriverRegistry()
        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )
        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.ELECTRONIC_LOAD,
            manufacturer="ITECH",
            model="IT8512A",
        )

        yield

        DeviceManager._clear_instance()
        DriverRegistry._clear_instance()

    @pytest.mark.asyncio
    async def setup_devices(self):
        """创建多个测试设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()

        # 创建电源设备
        await manager.create_device(
            DeviceConfig(
                device_id="PSU001",
                model="E36312A",
                manufacturer="Keysight",
                category=DeviceCategory.POWER_SUPPLY,
                connection_type=ConnectionType.TCPIP,
                protocol=ProtocolType.VISA,
                resource_string="TCPIP0::192.168.1.100::inst0::INSTR",
            )
        )

        # 创建电子负载
        await manager.create_device(
            DeviceConfig(
                device_id="LOAD001",
                model="IT8512A",
                manufacturer="ITECH",
                category=DeviceCategory.ELECTRONIC_LOAD,
                connection_type=ConnectionType.USB,
                protocol=ProtocolType.VISA,
                resource_string="USB0::0x1234::0x5678::SN123::INSTR",
            )
        )

        return manager

    @pytest.mark.asyncio
    async def test_get_device_by_id(self):
        """测试按 ID 获取设备"""
        manager = await self.setup_devices()

        driver = manager.get_device("PSU001")

        assert driver is not None
        assert driver.config.device_id == "PSU001"

    @pytest.mark.asyncio
    async def test_get_device_not_found(self):
        """测试获取不存在的设备"""
        manager = await self.setup_devices()

        driver = manager.get_device("NONEXISTENT")

        assert driver is None

    @pytest.mark.asyncio
    async def test_get_devices_by_category(self):
        """测试按类别获取设备"""
        manager = await self.setup_devices()

        drivers = manager.get_devices_by_category(DeviceCategory.POWER_SUPPLY)

        assert len(drivers) == 1
        assert drivers[0].config.device_id == "PSU001"

    @pytest.mark.asyncio
    async def test_get_devices_by_connection_type(self):
        """测试按连接类型获取设备"""
        manager = await self.setup_devices()

        drivers = manager.get_devices_by_connection_type(ConnectionType.TCPIP)

        assert len(drivers) == 1
        assert drivers[0].config.device_id == "PSU001"

    @pytest.mark.asyncio
    async def test_get_all_devices(self):
        """测试获取所有设备"""
        manager = await self.setup_devices()

        drivers = manager.get_all_devices()

        assert len(drivers) == 2

    @pytest.mark.asyncio
    async def test_get_device_ids(self):
        """测试获取所有设备 ID"""
        manager = await self.setup_devices()

        ids = manager.get_device_ids()

        assert len(ids) == 2
        assert "PSU001" in ids
        assert "LOAD001" in ids

    @pytest.mark.asyncio
    async def test_device_count(self):
        """测试设备计数"""
        manager = await self.setup_devices()

        assert manager.count() == 2


class TestCommandExecution:
    """命令执行测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清除管理器和注册表"""
        from modules.device.manager import DeviceManager
        from modules.device.registry import DriverRegistry

        DeviceManager._clear_instance()
        DriverRegistry._clear_instance()

        # 注册测试驱动
        registry = DriverRegistry()
        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )

        yield

        DeviceManager._clear_instance()
        DriverRegistry._clear_instance()

    @pytest.fixture
    async def manager_with_device(self):
        """创建带设备的管理器"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()
        await manager.create_device(
            DeviceConfig(
                device_id="PSU001",
                model="TestModel",
                manufacturer="TestManufacturer",
                category=DeviceCategory.POWER_SUPPLY,
                connection_type=ConnectionType.TCPIP,
                protocol=ProtocolType.VISA,
                resource_string="TCPIP0::192.168.1.100::inst0::INSTR",
            )
        )
        await manager.connect_device("PSU001")
        return manager

    @pytest.mark.asyncio
    async def test_execute_query_command(self, manager_with_device):
        """测试执行查询命令"""
        result = await manager_with_device.execute_command(
            "PSU001", "query", "*IDN?"
        )

        assert result == "OK"

    @pytest.mark.asyncio
    async def test_execute_write_command(self, manager_with_device):
        """测试执行写入命令"""
        # 不应抛出异常
        await manager_with_device.execute_command(
            "PSU001", "write", "*RST"
        )

    @pytest.mark.asyncio
    async def test_execute_read_command(self, manager_with_device):
        """测试执行读取命令"""
        result = await manager_with_device.execute_command(
            "PSU001", "read"
        )

        assert result == "OK"

    @pytest.mark.asyncio
    async def test_execute_command_device_not_found(self):
        """测试对不存在的设备执行命令"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()

        with pytest.raises(KeyError):
            await manager.execute_command("NONEXISTENT", "query", "*IDN?")

    @pytest.mark.asyncio
    async def test_execute_command_device_not_connected(self):
        """测试对未连接设备执行命令"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()
        await manager.create_device(
            DeviceConfig(
                device_id="PSU001",
                model="TestModel",
                manufacturer="TestManufacturer",
                category=DeviceCategory.POWER_SUPPLY,
                connection_type=ConnectionType.TCPIP,
                protocol=ProtocolType.VISA,
                resource_string="TCPIP0::192.168.1.100::inst0::INSTR",
            )
        )

        with pytest.raises(DeviceConnectionError):
            await manager.execute_command("PSU001", "query", "*IDN?")

    @pytest.mark.asyncio
    async def test_execute_invalid_command_type(self, manager_with_device):
        """测试执行无效命令类型"""
        with pytest.raises(ValueError, match="Unknown command type"):
            await manager_with_device.execute_command(
                "PSU001", "invalid_type", "command"
            )


class TestDeviceManagerUtilities:
    """设备管理器工具方法测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清除管理器和注册表"""
        from modules.device.manager import DeviceManager
        from modules.device.registry import DriverRegistry

        DeviceManager._clear_instance()
        DriverRegistry._clear_instance()

        # 注册测试驱动
        registry = DriverRegistry()
        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )

        yield

        DeviceManager._clear_instance()
        DriverRegistry._clear_instance()

    @pytest.mark.asyncio
    async def test_has_device(self):
        """测试检查设备是否存在"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()

        assert not manager.has_device("PSU001")

        await manager.create_device(
            DeviceConfig(
                device_id="PSU001",
                model="TestModel",
                manufacturer="TestManufacturer",
                category=DeviceCategory.POWER_SUPPLY,
                connection_type=ConnectionType.TCPIP,
                protocol=ProtocolType.VISA,
                resource_string="TCPIP0::192.168.1.100::inst0::INSTR",
            )
        )

        assert manager.has_device("PSU001")

    @pytest.mark.asyncio
    async def test_get_device_state(self):
        """测试获取设备状态"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()
        await manager.create_device(
            DeviceConfig(
                device_id="PSU001",
                model="TestModel",
                manufacturer="TestManufacturer",
                category=DeviceCategory.POWER_SUPPLY,
                connection_type=ConnectionType.TCPIP,
                protocol=ProtocolType.VISA,
                resource_string="TCPIP0::192.168.1.100::inst0::INSTR",
            )
        )

        state = manager.get_device_state("PSU001")
        assert state == DeviceState.DISCONNECTED

        await manager.connect_device("PSU001")
        state = manager.get_device_state("PSU001")
        assert state == DeviceState.CONNECTED

    @pytest.mark.asyncio
    async def test_get_device_state_not_found(self):
        """测试获取不存在设备的状态"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()

        state = manager.get_device_state("NONEXISTENT")
        assert state is None

    @pytest.mark.asyncio
    async def test_clear_all_devices(self):
        """测试清除所有设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()
        await manager.create_device(
            DeviceConfig(
                device_id="PSU001",
                model="TestModel",
                manufacturer="TestManufacturer",
                category=DeviceCategory.POWER_SUPPLY,
                connection_type=ConnectionType.TCPIP,
                protocol=ProtocolType.VISA,
                resource_string="TCPIP0::192.168.1.100::inst0::INSTR",
            )
        )

        await manager.clear()

        assert manager.count() == 0

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """测试断开所有设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()
        await manager.create_device(
            DeviceConfig(
                device_id="PSU001",
                model="TestModel",
                manufacturer="TestManufacturer",
                category=DeviceCategory.POWER_SUPPLY,
                connection_type=ConnectionType.TCPIP,
                protocol=ProtocolType.VISA,
                resource_string="TCPIP0::192.168.1.100::inst0::INSTR",
            )
        )
        await manager.connect_device("PSU001")

        await manager.disconnect_all()

        driver = manager.get_device("PSU001")
        assert driver is not None
        assert driver.state == DeviceState.DISCONNECTED


class TestDeviceManagerWithConfig:
    """设备管理器配置相关测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清除管理器和注册表"""
        from modules.device.manager import DeviceManager
        from modules.device.registry import DriverRegistry

        DeviceManager._clear_instance()
        DriverRegistry._clear_instance()

        # 注册测试驱动
        registry = DriverRegistry()
        registry.register_driver(
            driver_class=MockDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="TestManufacturer",
            model="TestModel",
        )

        yield

        DeviceManager._clear_instance()
        DriverRegistry._clear_instance()

    @pytest.mark.asyncio
    async def test_create_device_from_dict(self):
        """测试从字典创建设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()

        config_dict = {
            "device_id": "PSU001",
            "model": "TestModel",
            "manufacturer": "TestManufacturer",
            "category": "power_supply",
            "connection_type": "tcpip",
            "protocol": "visa",
            "resource_string": "TCPIP0::192.168.1.100::inst0::INSTR",
        }

        driver = await manager.create_device_from_dict(config_dict)

        assert driver is not None
        assert driver.config.device_id == "PSU001"

    @pytest.mark.asyncio
    async def test_create_devices_from_list(self):
        """测试从列表批量创建设备"""
        from modules.device.manager import DeviceManager

        manager = DeviceManager()

        configs = [
            {
                "device_id": "PSU001",
                "model": "TestModel",
                "manufacturer": "TestManufacturer",
                "category": "power_supply",
                "connection_type": "tcpip",
                "protocol": "visa",
                "resource_string": "TCPIP0::192.168.1.100::inst0::INSTR",
            },
            {
                "device_id": "PSU002",
                "model": "TestModel",
                "manufacturer": "TestManufacturer",
                "category": "power_supply",
                "connection_type": "tcpip",
                "protocol": "visa",
                "resource_string": "TCPIP0::192.168.1.101::inst0::INSTR",
            },
        ]

        drivers = await manager.create_devices_from_list(configs)

        assert len(drivers) == 2
        assert manager.count() == 2
