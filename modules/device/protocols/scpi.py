"""SCPI协议处理器

实现SCPI (Standard Commands for Programmable Instruments) 协议。
"""

import asyncio
import logging
from typing import Optional, Tuple
from modules.device.protocols.base_protocol import BaseProtocol


class SCPIProtocol(BaseProtocol):
    """SCPI协议处理器

    支持通过TCP/IP、USB、GPIB、VXI-11等多种方式连接SCPI设备。

    Attributes:
        _connection: 底层连接对象
        _lock: 异步锁，用于并发控制
        _logger: 日志记录器
    """

    def __init__(self):
        """初始化SCPI协议处理器"""
        self._connection = None
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connection is not None

    async def connect(self, resource_string: str) -> bool:
        """建立SCPI连接

        Args:
            resource_string: 资源标识符
                支持格式:
                - TCPIP0::192.168.1.100::5025::SOCKET
                - USB0::0x1234::0x5678::INSTR
                - GPIB0::1::INSTR

        Returns:
            连接是否成功
        """
        async with self._lock:
            try:
                if resource_string.startswith("TCPIP"):
                    return await self._connect_tcpip(resource_string)
                elif resource_string.startswith("USB"):
                    return await self._connect_usb(resource_string)
                elif resource_string.startswith("GPIB"):
                    return await self._connect_gpib(resource_string)
                else:
                    raise ValueError(f"Unsupported resource type: {resource_string}")
            except Exception as e:
                self._logger.error(f"Connection failed: {e}")
                return False

    async def disconnect(self) -> None:
        """断开连接"""
        async with self._lock:
            if self._connection:
                try:
                    # 如果连接对象有disconnect方法，调用它
                    if hasattr(self._connection, "disconnect"):
                        if asyncio.iscoroutinefunction(self._connection.disconnect):
                            await self._connection.disconnect()
                        else:
                            self._connection.disconnect()
                    # 如果有close方法，调用它
                    elif hasattr(self._connection, "close"):
                        if asyncio.iscoroutinefunction(self._connection.close):
                            await self._connection.close()
                        else:
                            self._connection.close()
                except Exception as e:
                    self._logger.error(f"Disconnect error: {e}")
                finally:
                    self._connection = None
                    self._logger.info("SCPI connection disconnected")

    async def write(self, command: str) -> None:
        """发送SCPI命令

        Args:
            command: SCPI命令字符串

        Raises:
            RuntimeError: 设备未连接
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to device")

        async with self._lock:
            try:
                # 添加换行符（SCPI标准）
                command_with_newline = command + "\n"

                # 根据连接类型发送命令
                if hasattr(self._connection, "write"):
                    if asyncio.iscoroutinefunction(self._connection.write):
                        await self._connection.write(command_with_newline.encode())
                    else:
                        self._connection.write(command_with_newline.encode())
                elif hasattr(self._connection, "send"):
                    if asyncio.iscoroutinefunction(self._connection.send):
                        await self._connection.send(command_with_newline.encode())
                    else:
                        self._connection.send(command_with_newline.encode())

                self._logger.debug(f"SCPI write: {command}")
            except Exception as e:
                self._logger.error(f"Write failed: {e}")
                raise

    async def read(self) -> str:
        """读取SCPI响应

        Returns:
            响应字符串（去除末尾换行符）

        Raises:
            RuntimeError: 设备未连接
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to device")

        async with self._lock:
            try:
                response = ""

                # 根据连接类型读取数据
                if hasattr(self._connection, "read"):
                    if asyncio.iscoroutinefunction(self._connection.read):
                        data = await self._connection.read(4096)
                    else:
                        data = self._connection.read(4096)
                    response = data.decode().strip()
                elif hasattr(self._connection, "recv"):
                    if asyncio.iscoroutinefunction(self._connection.recv):
                        data = await self._connection.recv(4096)
                    else:
                        data = self._connection.recv(4096)
                    response = data.decode().strip()

                self._logger.debug(f"SCPI read: {response}")
                return response
            except Exception as e:
                self._logger.error(f"Read failed: {e}")
                raise

    async def query(self, command: str) -> str:
        """SCPI查询命令（写后读）

        Args:
            command: 查询命令

        Returns:
            设备响应
        """
        await self.write(command)
        # SCPI命令通常需要短暂延迟
        await asyncio.sleep(0.01)
        return await self.read()

    # ============= 内部连接方法 =============

    async def _connect_tcpip(self, resource_string: str) -> bool:
        """TCP/IP连接

        Args:
            resource_string: TCP/IP资源字符串

        Returns:
            连接是否成功
        """
        try:
            host, port = self._parse_tcpip_resource(resource_string)

            self._logger.info(f"Connecting to TCP/IP {host}:{port}")

            # 创建TCP连接
            reader, writer = await asyncio.open_connection(host, port)

            # 存储连接对象（封装reader和writer）
            self._connection = _TCPConnection(reader, writer)

            self._logger.info(f"TCP/IP connection established to {host}:{port}")
            return True

        except Exception as e:
            self._logger.error(f"TCP/IP connection failed: {e}")
            return False

    async def _connect_usb(self, resource_string: str) -> bool:
        """USB连接（USBTMC）

        Args:
            resource_string: USB资源字符串

        Returns:
            连接是否成功
        """
        # 占位实现 - 需要实际的USB库支持
        self._logger.info(f"USB connection (placeholder): {resource_string}")

        # 创建模拟连接对象
        self._connection = _USBConnection()

        return True

    async def _connect_gpib(self, resource_string: str) -> bool:
        """GPIB连接

        Args:
            resource_string: GPIB资源字符串

        Returns:
            连接是否成功
        """
        # 占位实现 - 需要实际的GPIB库支持
        self._logger.info(f"GPIB connection (placeholder): {resource_string}")

        # 创建模拟连接对象
        self._connection = _GPIBConnection()

        return True

    def _parse_tcpip_resource(self, resource_string: str) -> Tuple[str, int]:
        """解析TCP/IP资源字符串

        Args:
            resource_string: TCP/IP资源字符串
                格式: TCPIP0::host::port::SOCKET 或 TCPIP0::host::INSTR

        Returns:
            (host, port) 元组
        """
        parts = resource_string.split("::")

        if len(parts) < 3:
            raise ValueError(f"Invalid TCP/IP resource: {resource_string}")

        host = parts[1]

        # 尝试解析端口
        if len(parts) > 2 and parts[2].isdigit():
            port = int(parts[2])
        else:
            # 默认端口5025 (LXI标准)
            port = 5025

        return host, port


class _TCPConnection:
    """TCP连接封装"""

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.is_connected = True

    async def write(self, data):
        self.writer.write(data)
        await self.writer.drain()

    async def read(self, size):
        return await self.reader.read(size)

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()


class _USBConnection:
    """USB连接占位实现"""

    def __init__(self):
        self.is_connected = True

    def write(self, data):
        pass

    def read(self, size):
        return b"+0"

    def close(self):
        pass


class _GPIBConnection:
    """GPIB连接占位实现"""

    def __init__(self):
        self.is_connected = True

    def write(self, data):
        pass

    def read(self, size):
        return b"+0"

    def close(self):
        pass


# 导出
__all__ = ["SCPIProtocol"]
