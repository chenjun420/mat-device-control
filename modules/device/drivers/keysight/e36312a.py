"""Keysight E36312A三通道可编程电源驱动

实现Keysight E36312A电源的完整驱动功能。
"""

from typing import Dict, Any
from modules.device.families.scpi_devices import SCPIDevice
from modules.device.base import DeviceConfig, DeviceConnectionError
from modules.device.enums import DeviceCategory


class KeysightE36312A(SCPIDevice):
    """Keysight E36312A三通道可编程电源驱动

    特性:
    - 3个独立输出通道
    - 通道1: 0-30V, 0-5A, 80W
    - 通道2: 0-30V, 0-5A, 80W
    - 通道3: 0-5V, 0-3A, 15W
    - 支持SCPI命令集

    Attributes:
        _channel_count: 通道数量
        _max_voltage: 每通道最大电压
        _max_current: 每通道最大电流
        _max_power: 每通道最大功率
    """

    def __init__(self, config: DeviceConfig):
        """初始化驱动

        Args:
            config: 设备配置
        """
        super().__init__(config)
        self._channel_count = 3
        self._max_voltage = [30.0, 30.0, 5.0]  # 每通道最大电压
        self._max_current = [5.0, 5.0, 3.0]  # 每通道最大电流
        self._max_power = [80.0, 80.0, 15.0]  # 每通道最大功率

    async def _connect_impl(self) -> bool:
        """连接并验证设备型号

        Returns:
            连接是否成功
        """
        # 先执行SCPI标准连接
        if not await super()._connect_impl():
            return False

        # 验证设备型号
        if "E36312A" not in self._model:
            raise DeviceConnectionError(
                f"Expected E36312A, got {self._model}", device_id=self.config.device_id
            )

        self._logger.info("Keysight E36312A connected successfully")
        return True

    # ============= 验证方法 =============

    def _validate_channel(self, channel: int) -> None:
        """验证通道号有效性

        Args:
            channel: 通道号

        Raises:
            ValueError: 通道号无效
        """
        if not 1 <= channel <= self._channel_count:
            raise ValueError(f"Channel must be 1-{self._channel_count}")

    def _validate_voltage(self, channel: int, voltage: float) -> None:
        """验证电压范围

        Args:
            channel: 通道号
            voltage: 电压值

        Raises:
            ValueError: 电压超出范围
        """
        max_v = self._max_voltage[channel - 1]
        if voltage < 0 or voltage > max_v:
            raise ValueError(f"Channel {channel} voltage must be 0-{max_v}V")

    def _validate_current(self, channel: int, current: float) -> None:
        """验证电流范围

        Args:
            channel: 通道号
            current: 电流值

        Raises:
            ValueError: 电流超出范围
        """
        max_i = self._max_current[channel - 1]
        if current < 0 or current > max_i:
            raise ValueError(f"Channel {channel} current must be 0-{max_i}A")

    # ============= 电源特定命令 =============

    async def set_voltage(self, channel: int, voltage: float) -> None:
        """设置通道电压

        Args:
            channel: 通道号 (1-3)
            voltage: 电压值 (V)
        """
        self._validate_channel(channel)
        self._validate_voltage(channel, voltage)

        await self.protocol.write(f"SOURCE{channel}:VOLTAGE {voltage:.3f}")
        self._logger.debug(f"Channel {channel} voltage set to {voltage}V")

    async def set_current(self, channel: int, current: float) -> None:
        """设置通道电流

        Args:
            channel: 通道号 (1-3)
            current: 电流值 (A)
        """
        self._validate_channel(channel)
        self._validate_current(channel, current)

        await self.protocol.write(f"SOURCE{channel}:CURRENT {current:.3f}")
        self._logger.debug(f"Channel {channel} current set to {current}A")

    async def enable_output(self, channel: int) -> None:
        """启用通道输出

        Args:
            channel: 通道号 (1-3)
        """
        self._validate_channel(channel)

        await self.protocol.write(f"OUTPUT{channel}:STATE ON")
        self._logger.info(f"Channel {channel} output enabled")

    async def disable_output(self, channel: int) -> None:
        """禁用通道输出

        Args:
            channel: 通道号 (1-3)
        """
        self._validate_channel(channel)

        await self.protocol.write(f"OUTPUT{channel}:STATE OFF")
        self._logger.info(f"Channel {channel} output disabled")

    async def measure_voltage(self, channel: int) -> float:
        """测量通道输出电压

        Args:
            channel: 通道号 (1-3)

        Returns:
            电压值 (V)
        """
        self._validate_channel(channel)

        response = await self.protocol.query(f"MEASURE{channel}:VOLTAGE?")
        voltage = float(response)
        self._logger.debug(f"Channel {channel} voltage measured: {voltage}V")
        return voltage

    async def measure_current(self, channel: int) -> float:
        """测量通道输出电流

        Args:
            channel: 通道号 (1-3)

        Returns:
            电流值 (A)
        """
        self._validate_channel(channel)

        response = await self.protocol.query(f"MEASURE{channel}:CURRENT?")
        current = float(response)
        self._logger.debug(f"Channel {channel} current measured: {current}A")
        return current

    async def measure_power(self, channel: int) -> float:
        """测量通道输出功率

        Args:
            channel: 通道号 (1-3)

        Returns:
            功率值 (W)
        """
        self._validate_channel(channel)

        response = await self.protocol.query(f"MEASURE{channel}:POWER?")
        power = float(response)
        self._logger.debug(f"Channel {channel} power measured: {power}W")
        return power

    async def get_output_state(self, channel: int) -> bool:
        """获取通道输出状态

        Args:
            channel: 通道号 (1-3)

        Returns:
            True如果输出启用，False如果禁用
        """
        self._validate_channel(channel)

        response = await self.protocol.query(f"OUTPUT{channel}:STATE?")
        return response.strip() in ("1", "ON", "TRUE")

    async def set_over_voltage_protection(self, channel: int, voltage: float) -> None:
        """设置过压保护

        Args:
            channel: 通道号 (1-3)
            voltage: 过压保护值 (V)
        """
        self._validate_channel(channel)
        self._validate_voltage(channel, voltage)

        await self.protocol.write(f"SOURCE{channel}:VOLTAGE:PROTECTION {voltage:.3f}")
        self._logger.debug(f"Channel {channel} OVP set to {voltage}V")

    async def set_over_current_protection(self, channel: int, current: float) -> None:
        """设置过流保护

        Args:
            channel: 通道号 (1-3)
            current: 过流保护值 (A)
        """
        self._validate_channel(channel)
        self._validate_current(channel, current)

        await self.protocol.write(f"SOURCE{channel}:CURRENT:PROTECTION {current:.3f}")
        self._logger.debug(f"Channel {channel} OCP set to {current}A")

    async def get_channel_info(self, channel: int) -> Dict[str, Any]:
        """获取通道信息

        Args:
            channel: 通道号 (1-3)

        Returns:
            通道信息字典
        """
        self._validate_channel(channel)

        voltage = await self.measure_voltage(channel)
        current = await self.measure_current(channel)
        power = await self.measure_power(channel)
        output_state = await self.get_output_state(channel)

        return {
            "channel": channel,
            "voltage": voltage,
            "current": current,
            "power": power,
            "output_enabled": output_state,
            "max_voltage": self._max_voltage[channel - 1],
            "max_current": self._max_current[channel - 1],
            "max_power": self._max_power[channel - 1],
        }


# 导出
__all__ = ["KeysightE36312A"]
