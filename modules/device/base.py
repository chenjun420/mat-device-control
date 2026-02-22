"""设备基础驱动类定义

提供设备驱动的抽象基类和核心数据结构：
- DeviceConfig: 设备配置数据类
- DeviceInfo: 设备信息数据类
- BaseDriver: 设备驱动抽象基类
- 设备异常类: DeviceError, DeviceConnectionError, DeviceTimeoutError, DeviceCommandError
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from modules.core.logging import get_logger
from modules.device.enums import (
    ConnectionType,
    DeviceCategory,
    DeviceState,
    ProtocolType,
)

logger = get_logger(__name__)


# ============================================================================
# 设备异常类
# ============================================================================


class DeviceError(Exception):
    """设备异常基类"""

    def __init__(self, message: str = "设备错误"):
        self.message = message
        super().__init__(self.message)


class DeviceConnectionError(DeviceError):
    """设备连接异常"""

    def __init__(
        self,
        message: str = "设备连接失败",
        device_id: str | None = None,
    ):
        self.device_id = device_id
        super().__init__(message)


class DeviceTimeoutError(DeviceError):
    """设备超时异常"""

    def __init__(
        self,
        message: str = "设备操作超时",
        device_id: str | None = None,
        timeout: float | None = None,
    ):
        self.device_id = device_id
        self.timeout = timeout
        super().__init__(message)


class DeviceCommandError(DeviceError):
    """设备命令异常"""

    def __init__(
        self,
        message: str = "设备命令执行失败",
        device_id: str | None = None,
        command: str | None = None,
    ):
        self.device_id = device_id
        self.command = command
        super().__init__(message)


# ============================================================================
# 设备配置数据类
# ============================================================================


@dataclass
class DeviceConfig:
    """设备配置数据类

    存储设备的连接配置和参数。

    Attributes:
        device_id: 设备唯一标识符
        model: 设备型号
        manufacturer: 制造商
        category: 设备类别
        connection_type: 连接类型
        protocol: 通信协议
        resource_string: VISA资源字符串
        timeout: 通信超时时间（秒）
        retry_count: 重试次数
        retry_delay: 重试延迟（秒）
        config: 额外配置参数
    """

    device_id: str
    model: str
    manufacturer: str
    category: DeviceCategory
    connection_type: ConnectionType
    protocol: ProtocolType
    resource_string: str
    timeout: float = 5.0
    retry_count: int = 3
    retry_delay: float = 0.5
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典

        Returns:
            包含所有配置的字典
        """
        return {
            "device_id": self.device_id,
            "model": self.model,
            "manufacturer": self.manufacturer,
            "category": self.category.value,
            "connection_type": self.connection_type.value,
            "protocol": self.protocol.value,
            "resource_string": self.resource_string,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeviceConfig":
        """从字典创建配置

        Args:
            data: 配置字典

        Returns:
            DeviceConfig 实例
        """
        return cls(
            device_id=data["device_id"],
            model=data["model"],
            manufacturer=data["manufacturer"],
            category=DeviceCategory(data["category"]),
            connection_type=ConnectionType(data["connection_type"]),
            protocol=ProtocolType(data["protocol"]),
            resource_string=data["resource_string"],
            timeout=data.get("timeout", 5.0),
            retry_count=data.get("retry_count", 3),
            retry_delay=data.get("retry_delay", 0.5),
            config=data.get("config", {}),
        )


# ============================================================================
# 设备信息数据类
# ============================================================================


@dataclass
class DeviceInfo:
    """设备信息数据类

    存储设备的标识信息。

    Attributes:
        device_id: 设备唯一标识符
        model: 设备型号
        manufacturer: 制造商
        serial_number: 序列号
        firmware_version: 固件版本
        category: 设备类别
    """

    device_id: str
    model: str
    manufacturer: str
    serial_number: str | None = None
    firmware_version: str | None = None
    category: DeviceCategory = DeviceCategory.GENERIC

    def to_dict(self) -> dict[str, Any]:
        """转换为字典

        Returns:
            包含所有信息的字典
        """
        return {
            "device_id": self.device_id,
            "model": self.model,
            "manufacturer": self.manufacturer,
            "serial_number": self.serial_number,
            "firmware_version": self.firmware_version,
            "category": self.category.value,
        }


# ============================================================================
# 设备驱动抽象基类
# ============================================================================


class BaseDriver(ABC):
    """设备驱动抽象基类

    所有设备驱动必须继承此类并实现抽象方法。
    提供设备生命周期管理和通信接口。

    Attributes:
        config: 设备配置
        state: 当前设备状态
    """

    def __init__(self, config: DeviceConfig):
        """初始化驱动

        Args:
            config: 设备配置
        """
        self._config = config
        self._state = DeviceState.DISCONNECTED
        self._device_info: DeviceInfo | None = None
        self._logger = get_logger(f"{__name__}.{config.device_id}")

    @property
    def config(self) -> DeviceConfig:
        """获取设备配置"""
        return self._config

    @property
    def state(self) -> DeviceState:
        """获取当前设备状态"""
        return self._state

    @state.setter
    def state(self, value: DeviceState) -> None:
        """设置设备状态"""
        old_state = self._state
        self._state = value
        self._logger.debug(
            "Device state changed",
            extra={
                "device_id": self._config.device_id,
                "old_state": old_state.value,
                "new_state": value.value,
            },
        )

    @property
    def is_connected(self) -> bool:
        """检查设备是否已连接"""
        return self._state.is_connected()

    # ========================================================================
    # 抽象方法 - 子类必须实现
    # ========================================================================

    @abstractmethod
    async def _connect_impl(self) -> bool:
        """连接实现（子类实现）

        Returns:
            连接是否成功
        """
        pass

    @abstractmethod
    async def _disconnect_impl(self) -> None:
        """断开连接实现（子类实现）"""
        pass

    @abstractmethod
    async def _write_impl(self, command: str) -> None:
        """写入命令实现（子类实现）

        Args:
            command: 要写入的命令
        """
        pass

    @abstractmethod
    async def _query_impl(self, command: str) -> str:
        """查询命令实现（子类实现）

        Args:
            command: 要查询的命令

        Returns:
            设备响应
        """
        pass

    @abstractmethod
    async def _read_impl(self) -> str:
        """读取数据实现（子类实现）

        Returns:
            读取的数据
        """
        pass

    # ========================================================================
    # 公共接口方法
    # ========================================================================

    async def connect(self) -> bool:
        """连接设备

        包含重试机制和状态管理。

        Returns:
            连接是否成功
        """
        if self.is_connected:
            self._logger.debug(
                "Device already connected",
                extra={"device_id": self._config.device_id},
            )
            return True

        self.state = DeviceState.CONNECTING
        last_error: Exception | None = None

        for attempt in range(self._config.retry_count):
            try:
                self._logger.debug(
                    "Attempting connection",
                    extra={
                        "device_id": self._config.device_id,
                        "attempt": attempt + 1,
                        "max_attempts": self._config.retry_count,
                    },
                )

                result = await self._connect_impl()

                if result:
                    self.state = DeviceState.CONNECTED
                    self._logger.info(
                        "Device connected successfully",
                        extra={
                            "device_id": self._config.device_id,
                            "resource": self._config.resource_string,
                        },
                    )
                    return True

            except Exception as e:
                last_error = e
                self._logger.warning(
                    f"Connection attempt failed: {e}",
                    extra={
                        "device_id": self._config.device_id,
                        "attempt": attempt + 1,
                    },
                )

            if attempt < self._config.retry_count - 1:
                import asyncio

                await asyncio.sleep(self._config.retry_delay)

        self.state = DeviceState.ERROR
        self._logger.error(
            "Failed to connect after all retries",
            extra={
                "device_id": self._config.device_id,
                "error": str(last_error),
            },
        )
        raise DeviceConnectionError(
            f"Failed to connect after {self._config.retry_count} attempts",
            device_id=self._config.device_id,
        )

    async def disconnect(self) -> None:
        """断开设备连接"""
        if not self.is_connected:
            return

        try:
            await self._disconnect_impl()
            self._logger.info(
                "Device disconnected",
                extra={"device_id": self._config.device_id},
            )
        finally:
            self.state = DeviceState.DISCONNECTED

    async def write(self, command: str) -> None:
        """写入命令到设备

        Args:
            command: 要写入的命令

        Raises:
            DeviceConnectionError: 设备未连接
        """
        if not self.is_connected:
            raise DeviceConnectionError(
                "Device not connected",
                device_id=self._config.device_id,
            )

        self.state = DeviceState.BUSY
        try:
            await self._write_impl(command)
            self._logger.debug(
                "Command written",
                extra={
                    "device_id": self._config.device_id,
                    "command": command[:50],  # Truncate long commands
                },
            )
        finally:
            self.state = DeviceState.CONNECTED

    async def query(self, command: str) -> str:
        """查询设备

        Args:
            command: 要查询的命令

        Returns:
            设备响应

        Raises:
            DeviceConnectionError: 设备未连接
        """
        if not self.is_connected:
            raise DeviceConnectionError(
                "Device not connected",
                device_id=self._config.device_id,
            )

        self.state = DeviceState.BUSY
        try:
            result = await self._query_impl(command)
            self._logger.debug(
                "Query executed",
                extra={
                    "device_id": self._config.device_id,
                    "command": command[:50],
                    "response": result[:50] if result else None,
                },
            )
            return result
        finally:
            self.state = DeviceState.CONNECTED

    async def read(self) -> str:
        """从设备读取数据

        Returns:
            读取的数据

        Raises:
            DeviceConnectionError: 设备未连接
        """
        if not self.is_connected:
            raise DeviceConnectionError(
                "Device not connected",
                device_id=self._config.device_id,
            )

        self.state = DeviceState.BUSY
        try:
            result = await self._read_impl()
            self._logger.debug(
                "Data read",
                extra={
                    "device_id": self._config.device_id,
                    "data": result[:50] if result else None,
                },
            )
            return result
        finally:
            self.state = DeviceState.CONNECTED

    async def get_device_info(self) -> DeviceInfo:
        """获取设备信息

        Returns:
            设备信息
        """
        if self._device_info is not None:
            return self._device_info

        # 默认实现：从配置创建基本信息
        self._device_info = DeviceInfo(
            device_id=self._config.device_id,
            model=self._config.model,
            manufacturer=self._config.manufacturer,
            category=self._config.category,
        )

        return self._device_info

    async def __aenter__(self) -> "BaseDriver":
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        await self.disconnect()


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "DeviceError",
    "DeviceConnectionError",
    "DeviceTimeoutError",
    "DeviceCommandError",
    "DeviceConfig",
    "DeviceInfo",
    "BaseDriver",
]
