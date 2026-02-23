"""协议抽象基类

定义所有设备通信协议必须实现的抽象接口。
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseProtocol(ABC):
    """设备通信协议抽象基类

    所有协议实现必须继承此类并实现抽象方法。
    提供设备生命周期管理和通信接口。

    Attributes:
        _connection: 底层连接对象
        _logger: 日志记录器
    """

    @abstractmethod
    async def connect(self, resource_string: str) -> bool:
        """建立连接

        Args:
            resource_string: 资源标识符
                (如 "TCPIP0::192.168.1.100::5025::SOCKET")

        Returns:
            连接是否成功
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def write(self, command: str) -> None:
        """发送命令

        Args:
            command: 要发送的命令字符串
        """
        pass

    @abstractmethod
    async def read(self) -> str:
        """读取响应

        Returns:
            读取到的响应字符串
        """
        pass

    @abstractmethod
    async def query(self, command: str) -> str:
        """查询命令 (写后读)

        Args:
            command: 查询命令

        Returns:
            设备响应
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """检查是否已连接

        Returns:
            True如果已连接，False否则
        """
        pass


# 导出
__all__ = ["BaseProtocol"]
