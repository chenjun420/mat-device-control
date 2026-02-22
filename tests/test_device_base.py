"""设备基础驱动类单元测试"""


import pytest

from modules.device.base import (
    BaseDriver,
    DeviceConfig,
    DeviceInfo,
    DeviceError,
    DeviceConnectionError,
    DeviceTimeoutError,
    DeviceCommandError,
)
from modules.device.enums import (
    ConnectionType,
    DeviceCategory,
    DeviceState,
    ProtocolType,
)


class TestDeviceConfig:
    """DeviceConfig 测试类"""

    def test_device_config_creation(self):
        """测试设备配置创建"""
        config = DeviceConfig(
            device_id="PSU001",
            model="Keysight E36312A",
            manufacturer="Keysight",
            category=DeviceCategory.POWER_SUPPLY,
            connection_type=ConnectionType.TCPIP,
            protocol=ProtocolType.VISA,
            resource_string="TCPIP0::192.168.1.100::inst0::INSTR",
        )

        assert config.device_id == "PSU001"
        assert config.model == "Keysight E36312A"
        assert config.manufacturer == "Keysight"
        assert config.category == DeviceCategory.POWER_SUPPLY
        assert config.connection_type == ConnectionType.TCPIP
        assert config.protocol == ProtocolType.VISA
        assert config.resource_string == "TCPIP0::192.168.1.100::inst0::INSTR"

    def test_device_config_defaults(self):
        """测试设备配置默认值"""
        config = DeviceConfig(
            device_id="DEV001",
            model="Generic Device",
            manufacturer="Unknown",
            category=DeviceCategory.GENERIC,
            connection_type=ConnectionType.TCPIP,
            protocol=ProtocolType.VISA,
            resource_string="TCPIP0::localhost::INSTR",
        )

        assert config.timeout == 5.0
        assert config.retry_count == 3
        assert config.retry_delay == 0.5
        assert config.config == {}

    def test_device_config_custom_timeout(self):
        """测试自定义超时配置"""
        config = DeviceConfig(
            device_id="DEV001",
            model="Test Device",
            manufacturer="Test",
            category=DeviceCategory.GENERIC,
            connection_type=ConnectionType.SERIAL,
            protocol=ProtocolType.MODBUS_RTU,
            resource_string="ASRL1::INSTR",
            timeout=10.0,
            retry_count=5,
            retry_delay=1.0,
        )

        assert config.timeout == 10.0
        assert config.retry_count == 5
        assert config.retry_delay == 1.0

    def test_device_config_to_dict(self):
        """测试设备配置转换为字典"""
        config = DeviceConfig(
            device_id="PSU001",
            model="Keysight E36312A",
            manufacturer="Keysight",
            category=DeviceCategory.POWER_SUPPLY,
            connection_type=ConnectionType.TCPIP,
            protocol=ProtocolType.VISA,
            resource_string="TCPIP0::192.168.1.100::inst0::INSTR",
        )

        result = config.to_dict()

        assert result["device_id"] == "PSU001"
        assert result["model"] == "Keysight E36312A"
        assert result["category"] == "power_supply"
        assert result["connection_type"] == "tcpip"
        assert result["protocol"] == "visa"

    def test_device_config_from_dict(self):
        """测试从字典创建设备配置"""
        data = {
            "device_id": "LOAD001",
            "model": "IT8512A+",
            "manufacturer": "ITECH",
            "category": "electronic_load",
            "connection_type": "usb",
            "protocol": "visa",
            "resource_string": "USB0::0x1234::0x5678::SN123::INSTR",
            "timeout": 8.0,
        }

        config = DeviceConfig.from_dict(data)

        assert config.device_id == "LOAD001"
        assert config.model == "IT8512A+"
        assert config.category == DeviceCategory.ELECTRONIC_LOAD
        assert config.connection_type == ConnectionType.USB
        assert config.timeout == 8.0


class TestDeviceInfo:
    """DeviceInfo 测试类"""

    def test_device_info_creation(self):
        """测试设备信息创建"""
        info = DeviceInfo(
            device_id="PSU001",
            model="Keysight E36312A",
            manufacturer="Keysight",
            serial_number="MY12345678",
            firmware_version="1.2.3",
            category=DeviceCategory.POWER_SUPPLY,
        )

        assert info.device_id == "PSU001"
        assert info.model == "Keysight E36312A"
        assert info.serial_number == "MY12345678"
        assert info.firmware_version == "1.2.3"

    def test_device_info_to_dict(self):
        """测试设备信息转换为字典"""
        info = DeviceInfo(
            device_id="PSU001",
            model="Keysight E36312A",
            manufacturer="Keysight",
            serial_number="MY12345678",
            firmware_version="1.2.3",
            category=DeviceCategory.POWER_SUPPLY,
        )

        result = info.to_dict()

        assert result["device_id"] == "PSU001"
        assert result["serial_number"] == "MY12345678"
        assert result["firmware_version"] == "1.2.3"


class TestDeviceExceptions:
    """设备异常测试类"""

    def test_device_error(self):
        """测试设备基础异常"""
        error = DeviceError("Device error occurred")
        assert str(error) == "Device error occurred"
        assert isinstance(error, Exception)

    def test_device_connection_error(self):
        """测试设备连接异常"""
        error = DeviceConnectionError("Failed to connect", device_id="PSU001")
        assert str(error) == "Failed to connect"
        assert error.device_id == "PSU001"
        assert isinstance(error, DeviceError)

    def test_device_timeout_error(self):
        """测试设备超时异常"""
        error = DeviceTimeoutError(
            "Operation timed out", device_id="PSU001", timeout=5.0
        )
        assert str(error) == "Operation timed out"
        assert error.device_id == "PSU001"
        assert error.timeout == 5.0
        assert isinstance(error, DeviceError)

    def test_device_command_error(self):
        """测试设备命令异常"""
        error = DeviceCommandError(
            "Invalid command",
            device_id="PSU001",
            command="INVALID_CMD",
        )
        assert str(error) == "Invalid command"
        assert error.device_id == "PSU001"
        assert error.command == "INVALID_CMD"
        assert isinstance(error, DeviceError)


class ConcreteDriver(BaseDriver):
    """用于测试的具体驱动实现"""

    async def _connect_impl(self) -> bool:
        """连接实现"""
        return True

    async def _disconnect_impl(self) -> None:
        """断开连接实现"""
        pass

    async def _write_impl(self, command: str) -> None:
        """写入实现"""
        pass

    async def _query_impl(self, command: str) -> str:
        """查询实现"""
        return "OK"

    async def _read_impl(self) -> str:
        """读取实现"""
        return "OK"


class TestBaseDriver:
    """BaseDriver 测试类"""

    @pytest.fixture
    def device_config(self):
        """创建测试设备配置"""
        return DeviceConfig(
            device_id="TEST001",
            model="Test Device",
            manufacturer="Test",
            category=DeviceCategory.GENERIC,
            connection_type=ConnectionType.TCPIP,
            protocol=ProtocolType.VISA,
            resource_string="TCPIP0::localhost::INSTR",
        )

    @pytest.fixture
    def driver(self, device_config):
        """创建测试驱动实例"""
        return ConcreteDriver(device_config)

    def test_driver_initialization(self, driver, device_config):
        """测试驱动初始化"""
        assert driver.config == device_config
        assert driver.state == DeviceState.DISCONNECTED
        assert driver._device_info is None

    def test_driver_state_property(self, driver):
        """测试驱动状态属性"""
        assert driver.state == DeviceState.DISCONNECTED

        driver._state = DeviceState.CONNECTED
        assert driver.state == DeviceState.CONNECTED

    @pytest.mark.asyncio
    async def test_driver_connect(self, driver):
        """测试驱动连接"""
        result = await driver.connect()

        assert result is True
        assert driver.state == DeviceState.CONNECTED

    @pytest.mark.asyncio
    async def test_driver_disconnect(self, driver):
        """测试驱动断开连接"""
        await driver.connect()
        await driver.disconnect()

        assert driver.state == DeviceState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_driver_write(self, driver):
        """测试驱动写入"""
        await driver.connect()
        await driver.write("*IDN?")

        # 不应抛出异常

    @pytest.mark.asyncio
    async def test_driver_query(self, driver):
        """测试驱动查询"""
        await driver.connect()
        result = await driver.query("*IDN?")

        assert result == "OK"

    @pytest.mark.asyncio
    async def test_driver_read(self, driver):
        """测试驱动读取"""
        await driver.connect()
        result = await driver.read()

        assert result == "OK"

    @pytest.mark.asyncio
    async def test_driver_write_not_connected(self, driver):
        """测试未连接时写入"""
        with pytest.raises(DeviceConnectionError):
            await driver.write("*IDN?")

    @pytest.mark.asyncio
    async def test_driver_query_not_connected(self, driver):
        """测试未连接时查询"""
        with pytest.raises(DeviceConnectionError):
            await driver.query("*IDN?")

    @pytest.mark.asyncio
    async def test_driver_context_manager(self, driver):
        """测试上下文管理器"""
        async with driver as d:
            assert d.state == DeviceState.CONNECTED

        assert driver.state == DeviceState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_driver_get_device_info(self, driver):
        """测试获取设备信息"""
        await driver.connect()
        info = await driver.get_device_info()

        assert info is not None
        assert info.device_id == driver.config.device_id

    def test_driver_is_connected(self, driver):
        """测试连接状态检查"""
        assert not driver.is_connected

        driver._state = DeviceState.CONNECTED
        assert driver.is_connected

        driver._state = DeviceState.READY
        assert driver.is_connected

        driver._state = DeviceState.DISCONNECTED
        assert not driver.is_connected


class TestBaseDriverAbstract:
    """BaseDriver 抽象类测试"""

    def test_cannot_instantiate_abstract(self):
        """测试不能直接实例化抽象类"""
        config = DeviceConfig(
            device_id="TEST001",
            model="Test",
            manufacturer="Test",
            category=DeviceCategory.GENERIC,
            connection_type=ConnectionType.TCPIP,
            protocol=ProtocolType.VISA,
            resource_string="TCPIP0::localhost::INSTR",
        )

        with pytest.raises(TypeError):
            BaseDriver(config)  # type: ignore

    def test_subclass_must_implement_methods(self):
        """测试子类必须实现所有抽象方法"""

        class IncompleteDriver(BaseDriver):
            pass

        config = DeviceConfig(
            device_id="TEST001",
            model="Test",
            manufacturer="Test",
            category=DeviceCategory.GENERIC,
            connection_type=ConnectionType.TCPIP,
            protocol=ProtocolType.VISA,
            resource_string="TCPIP0::localhost::INSTR",
        )

        with pytest.raises(TypeError):
            IncompleteDriver(config)  # type: ignore


class TestBaseDriverRetry:
    """BaseDriver 重试机制测试"""

    @pytest.fixture
    def device_config(self):
        """创建测试设备配置"""
        return DeviceConfig(
            device_id="TEST001",
            model="Test Device",
            manufacturer="Test",
            category=DeviceCategory.GENERIC,
            connection_type=ConnectionType.TCPIP,
            protocol=ProtocolType.VISA,
            resource_string="TCPIP0::localhost::INSTR",
            retry_count=3,
            retry_delay=0.1,
        )

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, device_config):
        """测试失败重试机制"""

        class FailingDriver(BaseDriver):
            def __init__(self, config):
                super().__init__(config)
                self.attempt_count = 0

            async def _connect_impl(self) -> bool:
                self.attempt_count += 1
                if self.attempt_count < 3:
                    raise DeviceConnectionError("Connection failed")
                return True

            async def _disconnect_impl(self) -> None:
                pass

            async def _write_impl(self, command: str) -> None:
                pass

            async def _query_impl(self, command: str) -> str:
                return "OK"

            async def _read_impl(self) -> str:
                return "OK"

        driver = FailingDriver(device_config)
        result = await driver.connect()

        assert result is True
        assert driver.attempt_count == 3
