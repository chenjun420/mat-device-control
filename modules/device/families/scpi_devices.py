"""SCPI设备族实现

提供所有SCPI设备的基础类和通用功能。
"""

import asyncio
from typing import Optional
from modules.device.base import BaseDriver, DeviceConfig, DeviceInfo
from modules.device.protocols.scpi import SCPIProtocol


class SCPIDevice(BaseDriver):
    """SCPI设备族基类

    所有SCPI设备驱动的基础类，提供SCPI协议通用功能。

    Attributes:
        protocol: SCPI协议处理器
        _manufacturer: 制造商
        _model: 型号
        _serial_number: 序列号
        _firmware_version: 固件版本
    """

    def __init__(self, config: DeviceConfig):
        """初始化SCPI设备

        Args:
            config: 设备配置
        """
        super().__init__(config)
        self.protocol = SCPIProtocol()
        self._manufacturer = ""
        self._model = ""
        self._serial_number = ""
        self._firmware_version = ""

    async def _connect_impl(self) -> bool:
        """SCPI连接实现

        Returns:
            连接是否成功
        """
        try:
            # 建立协议连接
            if not await self.protocol.connect(self.config.resource_string):
                return False

            # 识别设备
            await self._identify_device()

            self._logger.info(
                "SCPI device connected",
                extra={
                    "device_id": self.config.device_id,
                    "manufacturer": self._manufacturer,
                    "model": self._model,
                    "serial": self._serial_number,
                    "firmware": self._firmware_version,
                },
            )
            return True

        except Exception as e:
            self._logger.error(f"SCPI device connection failed: {e}")
            return False

    async def _disconnect_impl(self) -> None:
        """断开连接实现"""
        if self.protocol:
            await self.protocol.disconnect()

    async def _write_impl(self, command: str) -> None:
        """写入命令实现

        Args:
            command: 命令字符串
        """
        await self.protocol.write(command)

    async def _query_impl(self, command: str) -> str:
        """查询命令实现

        Args:
            command: 查询命令

        Returns:
            设备响应
        """
        return await self.protocol.query(command)

    async def _read_impl(self) -> str:
        """读取数据实现

        Returns:
            读取的数据
        """
        return await self.protocol.read()

    # ============= SCPI通用命令 =============

    async def _identify_device(self) -> None:
        """设备识别

        使用*IDN?命令获取设备身份信息。
        响应格式: MANUFACTURER,MODEL,SERIAL_NUMBER,FIRMWARE_VERSION
        """
        try:
            idn_response = await self.protocol.query("*IDN?")
            parts = [part.strip() for part in idn_response.split(",")]

            if len(parts) >= 4:
                self._manufacturer = parts[0]
                self._model = parts[1]
                self._serial_number = parts[2]
                self._firmware_version = parts[3]
            elif len(parts) >= 2:
                self._manufacturer = parts[0]
                self._model = parts[1]
                self._serial_number = parts[2] if len(parts) > 2 else ""
                self._firmware_version = parts[3] if len(parts) > 3 else ""
            else:
                self._logger.warning(f"Unexpected IDN format: {idn_response}")

        except Exception as e:
            self._logger.error(f"Device identification failed: {e}")
            # 使用配置信息作为备选
            self._manufacturer = self.config.manufacturer
            self._model = self.config.model

    async def reset(self) -> None:
        """设备复位

        发送*RST命令重置设备到默认状态。
        """
        await self.protocol.write("*RST")
        # 等待复位完成
        await asyncio.sleep(0.5)
        self._logger.info("Device reset completed")

    async def wait_for_operation_complete(self) -> None:
        """等待操作完成

        使用*OPC?命令等待所有未完成的操作完成。
        """
        await self.protocol.query("*OPC?")

    async def get_error(self) -> Optional[str]:
        """获取错误信息

        Returns:
            错误信息字符串，如果没有错误返回None
        """
        try:
            error_response = await self.protocol.query("SYSTEM:ERROR?")
            # 格式: +0,"No error" 或 +123,"Error message"
            if error_response.startswith("+0,") or "No error" in error_response:
                return None
            else:
                return error_response
        except Exception as e:
            self._logger.error(f"Failed to get error: {e}")
            return f"Error query failed: {e}"

    async def clear_status(self) -> None:
        """清除状态寄存器"""
        await self.protocol.write("*CLS")

    async def get_device_info(self) -> DeviceInfo:
        """获取设备信息

        重写基类方法，使用SCPI识别信息。

        Returns:
            设备信息对象
        """
        return DeviceInfo(
            device_id=self.config.device_id,
            model=self._model or self.config.model,
            manufacturer=self._manufacturer or self.config.manufacturer,
            serial_number=self._serial_number,
            firmware_version=self._firmware_version,
            category=self.config.category,
        )


# 导出
__all__ = ["SCPIDevice"]
