"""通用 SCPI 可编程电源驱动（ATEStudio edge 通用设备契约适配）。

背景
----
ATEStudio edge 的
:class:`~ate_platform.drivers.mat_device.http_driver.MatDeviceHttpDriver` 把一次
设备方法调用转成一次 HTTP POST ``/devices/{id}/call``，请求体的 ``kwargs`` 使用
**通用设备契约**命名：

* ``set_voltage(value, channel?)``
* ``set_current(value, channel?)``
* ``measure_voltage(channel?)``
* ``measure_current(channel?)``

本驱动即该通用契约在 mat-device-control 侧的实现：把 ``value`` 语义翻译为标准
SCPI 命令（``SOURce{n}:VOLTage`` / ``MEASure{n}:VOLTage?``），经
:class:`SCPIProtocol` 发往真实仪器（或被 SCPI 反射服务器替代）。

与厂商驱动（如 :class:`~modules.device.drivers.keysight.e36312a.KeysightE36312A`）
的区别：厂商驱动使用厂商命名（``voltage`` 而非 ``value``）并校验通道规格；
本驱动只实现通用契约，不做型号校验，因而可直接对接任意 SCPI 电源，或在无实机
时对接反射服务器。
"""

from modules.device.base import DeviceConfig
from modules.device.families.scpi_devices import SCPIDevice


class GenericSCPIPowerSupply(SCPIDevice):
    """通用 SCPI 电源驱动（单通道语义，可选通道号）。

    Attributes:
        _channel_count: 支持的通道数（通用驱动固定为 1）。
    """

    #: 通用驱动固定单通道；SCPI 命令仍携带通道号以兼容多通道仪器。
    _channel_count = 1

    def __init__(self, config: DeviceConfig):
        """初始化通用电源驱动。

        Args:
            config: 设备配置。
        """
        super().__init__(config)

    def _validate_channel(self, channel: int) -> None:
        """校验通道号。

        Args:
            channel: 通道号（须为正整数）。

        Raises:
            ValueError: 通道号非法。
        """
        if channel < 1:
            raise ValueError(f"Channel must be >= 1, got {channel}")

    async def set_voltage(self, value: float, channel: int = 1) -> None:
        """设置输出电压。

        Args:
            value: 目标电压（伏）。
            channel: 通道号（默认 1）。

        Raises:
            ValueError: 通道号非法或电压为负。
        """
        self._validate_channel(channel)
        if value < 0:
            raise ValueError(f"Voltage must be >= 0, got {value}")
        await self.protocol.write(f"SOURce{channel}:VOLTage {value:.3f}")
        self._logger.debug(f"channel {channel} voltage set to {value}V")

    async def set_current(self, value: float, channel: int = 1) -> None:
        """设置输出电流限值。

        Args:
            value: 目标电流（安）。
            channel: 通道号（默认 1）。

        Raises:
            ValueError: 通道号非法或电流为负。
        """
        self._validate_channel(channel)
        if value < 0:
            raise ValueError(f"Current must be >= 0, got {value}")
        await self.protocol.write(f"SOURce{channel}:CURRent {value:.3f}")
        self._logger.debug(f"channel {channel} current set to {value}A")

    async def enable_output(self, enable: bool, channel: int = 1) -> None:
        """使能 / 关闭输出。

        Args:
            enable: True 使能，False 关闭。
            channel: 通道号（默认 1）。

        Raises:
            ValueError: 通道号非法。
        """
        self._validate_channel(channel)
        state = "ON" if enable else "OFF"
        await self.protocol.write(f"OUTPut{channel}:STATe {state}")
        self._logger.debug(f"channel {channel} output {state}")

    async def measure_voltage(self, channel: int = 1) -> float:
        """测量输出电压。

        Args:
            channel: 通道号（默认 1）。

        Returns:
            测得电压（伏）。

        Raises:
            ValueError: 通道号非法。
        """
        self._validate_channel(channel)
        response = await self.protocol.query(f"MEASure{channel}:VOLTage?")
        voltage = float(response)
        self._logger.debug(f"channel {channel} voltage measured: {voltage}V")
        return voltage

    async def measure_current(self, channel: int = 1) -> float:
        """测量输出电流。

        Args:
            channel: 通道号（默认 1）。

        Returns:
            测得电流（安）。

        Raises:
            ValueError: 通道号非法。
        """
        self._validate_channel(channel)
        response = await self.protocol.query(f"MEASure{channel}:CURRent?")
        current = float(response)
        self._logger.debug(f"channel {channel} current measured: {current}A")
        return current


# 导出
__all__ = ["GenericSCPIPowerSupply"]
