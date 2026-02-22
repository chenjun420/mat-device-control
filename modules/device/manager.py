"""设备管理器

提供设备生命周期管理功能：
- DeviceManager: 设备管理器单例
- 设备创建、连接、断开、移除
- 设备查询（按ID、类别、连接类型）
- 命令执行接口
"""

from threading import Lock
from typing import Any

from modules.core.logging import get_logger
from modules.device.base import (
    BaseDriver,
    DeviceConfig,
    DeviceConnectionError,
)
from modules.device.enums import ConnectionType, DeviceCategory, DeviceState
from modules.device.registry import DriverRegistry

logger = get_logger(__name__)


class DeviceManager:
    """设备管理器

    单例模式实现的设备管理器，提供：
    - 设备生命周期管理（创建、连接、断开、移除）
    - 设备查询（按ID、类别、连接类型）
    - 命令执行接口

    Usage:
        manager = DeviceManager()
        driver = await manager.create_device(config)
        await manager.connect_device("PSU001")
        result = await manager.execute_command("PSU001", "query", "*IDN?")
    """

    _instance: "DeviceManager | None" = None
    _lock: Lock = Lock()

    def __new__(cls) -> "DeviceManager":
        """创建单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._devices: dict[str, BaseDriver] = {}
                    cls._instance._initialized = True
        return cls._instance

    @classmethod
    def get_instance(cls) -> "DeviceManager":
        """获取单例实例

        Returns:
            DeviceManager 单例实例
        """
        return cls()

    @classmethod
    def _clear_instance(cls) -> None:
        """清除单例实例（仅用于测试）"""
        with cls._lock:
            cls._instance = None

    async def create_device(self, config: DeviceConfig) -> BaseDriver:
        """创建设备

        Args:
            config: 设备配置

        Returns:
            创建的驱动实例

        Raises:
            ValueError: 设备已存在
            KeyError: 未找到匹配的驱动
        """
        if config.device_id in self._devices:
            raise ValueError(f"Device '{config.device_id}' already exists")

        # 从注册表获取驱动类
        registry = DriverRegistry()
        driver_class = registry.get_driver(
            category=config.category,
            manufacturer=config.manufacturer,
            model=config.model,
        )

        if driver_class is None:
            raise KeyError(
                f"No driver found for {config.category.value}/{config.manufacturer}/{config.model}"
            )

        # 创建驱动实例
        driver = driver_class(config)
        self._devices[config.device_id] = driver

        logger.info(
            "Device created",
            extra={
                "device_id": config.device_id,
                "model": config.model,
                "manufacturer": config.manufacturer,
            },
        )

        return driver

    async def create_device_from_dict(
        self, config_dict: dict[str, Any]
    ) -> BaseDriver:
        """从字典创建设备

        Args:
            config_dict: 设备配置字典

        Returns:
            创建的驱动实例
        """
        config = DeviceConfig.from_dict(config_dict)
        return await self.create_device(config)

    async def create_devices_from_list(
        self, configs: list[dict[str, Any]]
    ) -> list[BaseDriver]:
        """批量创建设备

        Args:
            configs: 设备配置字典列表

        Returns:
            创建的驱动实例列表
        """
        drivers = []
        for config_dict in configs:
            driver = await self.create_device_from_dict(config_dict)
            drivers.append(driver)
        return drivers

    async def remove_device(self, device_id: str) -> bool:
        """移除设备

        Args:
            device_id: 设备ID

        Returns:
            是否成功移除
        """
        if device_id not in self._devices:
            return False

        # 先断开连接
        driver = self._devices[device_id]
        if driver.is_connected:
            await driver.disconnect()

        del self._devices[device_id]
        logger.info("Device removed", extra={"device_id": device_id})
        return True

    async def connect_device(self, device_id: str) -> bool:
        """连接设备

        Args:
            device_id: 设备ID

        Returns:
            是否成功连接

        Raises:
            KeyError: 设备不存在
        """
        if device_id not in self._devices:
            raise KeyError(f"Device '{device_id}' not found")

        driver = self._devices[device_id]
        result = await driver.connect()

        logger.info(
            "Device connected",
            extra={"device_id": device_id, "success": result},
        )

        return result

    async def disconnect_device(self, device_id: str) -> None:
        """断开设备连接

        Args:
            device_id: 设备ID
        """
        if device_id not in self._devices:
            return

        driver = self._devices[device_id]
        await driver.disconnect()

        logger.info("Device disconnected", extra={"device_id": device_id})

    async def disconnect_all(self) -> None:
        """断开所有设备连接"""
        for device_id, driver in self._devices.items():
            if driver.is_connected:
                await driver.disconnect()
                logger.debug("Device disconnected", extra={"device_id": device_id})

    def get_device(self, device_id: str) -> BaseDriver | None:
        """获取设备

        Args:
            device_id: 设备ID

        Returns:
            驱动实例，如果未找到返回 None
        """
        return self._devices.get(device_id)

    def get_devices_by_category(
        self, category: DeviceCategory
    ) -> list[BaseDriver]:
        """按类别获取设备

        Args:
            category: 设备类别

        Returns:
            该类别下的所有驱动实例列表
        """
        return [
            driver
            for driver in self._devices.values()
            if driver.config.category == category
        ]

    def get_devices_by_connection_type(
        self, connection_type: ConnectionType
    ) -> list[BaseDriver]:
        """按连接类型获取设备

        Args:
            connection_type: 连接类型

        Returns:
            该连接类型的所有驱动实例列表
        """
        return [
            driver
            for driver in self._devices.values()
            if driver.config.connection_type == connection_type
        ]

    def get_all_devices(self) -> list[BaseDriver]:
        """获取所有设备

        Returns:
            所有驱动实例列表
        """
        return list(self._devices.values())

    def get_device_ids(self) -> list[str]:
        """获取所有设备ID

        Returns:
            设备ID列表
        """
        return list(self._devices.keys())

    def has_device(self, device_id: str) -> bool:
        """检查设备是否存在

        Args:
            device_id: 设备ID

        Returns:
            设备是否存在
        """
        return device_id in self._devices

    def get_device_state(self, device_id: str) -> DeviceState | None:
        """获取设备状态

        Args:
            device_id: 设备ID

        Returns:
            设备状态，如果设备不存在返回 None
        """
        driver = self._devices.get(device_id)
        return driver.state if driver else None

    def count(self) -> int:
        """获取设备数量

        Returns:
            设备数量
        """
        return len(self._devices)

    async def clear(self) -> None:
        """清除所有设备"""
        await self.disconnect_all()
        self._devices.clear()
        logger.info("All devices cleared")

    async def execute_command(
        self,
        device_id: str,
        command_type: str,
        command: str | None = None,
    ) -> Any:
        """执行设备命令

        Args:
            device_id: 设备ID
            command_type: 命令类型 (query, write, read)
            command: 命令内容（query 和 write 需要）

        Returns:
            命令执行结果

        Raises:
            KeyError: 设备不存在
            DeviceConnectionError: 设备未连接
            ValueError: 无效的命令类型
        """
        if device_id not in self._devices:
            raise KeyError(f"Device '{device_id}' not found")

        driver = self._devices[device_id]

        if not driver.is_connected:
            raise DeviceConnectionError(
                f"Device '{device_id}' is not connected",
                device_id=device_id,
            )

        logger.debug(
            "Executing command",
            extra={
                "device_id": device_id,
                "command_type": command_type,
                "command": command[:50] if command else None,
            },
        )

        if command_type == "query":
            if command is None:
                raise ValueError("query command requires 'command' parameter")
            return await driver.query(command)
        elif command_type == "write":
            if command is None:
                raise ValueError("write command requires 'command' parameter")
            await driver.write(command)
            return None
        elif command_type == "read":
            return await driver.read()
        else:
            raise ValueError(f"Unknown command type: {command_type}")


# 导出
__all__ = [
    "DeviceManager",
]
