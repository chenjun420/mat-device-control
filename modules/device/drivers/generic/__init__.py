"""通用设备驱动子包。

提供与 ATEStudio edge 通用设备契约对齐的驱动：远端（mat-device-control）
以 ``set_voltage(value, channel?)`` / ``measure_voltage(channel?)`` 等通用语义
被调用，内部翻译为 SCPI 命令。
"""

from modules.device.drivers.generic.scpi_psu import GenericSCPIPowerSupply

__all__ = ["GenericSCPIPowerSupply"]
