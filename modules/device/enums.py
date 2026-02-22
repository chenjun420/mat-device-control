"""设备枚举类型定义

定义设备管理系统的核心枚举类型：
- DeviceCategory: 设备类别
- ConnectionType: 连接类型
- ProtocolType: 通信协议类型
- DeviceState: 设备状态
"""

from enum import Enum


class DeviceCategory(str, Enum):
    """设备类别枚举

    定义支持的测试设备类型。
    """

    POWER_SUPPLY = "power_supply"
    ELECTRONIC_LOAD = "electronic_load"
    POWER_METER = "power_meter"
    SIGNAL_GENERATOR = "signal_generator"
    SPECTRUM_ANALYZER = "spectrum_analyzer"
    MULTIMETER = "multimeter"
    OSCILLOSCOPE = "oscilloscope"
    GENERIC = "generic"


class ConnectionType(str, Enum):
    """连接类型枚举

    定义设备支持的物理连接方式。
    """

    TCPIP = "tcpip"
    USB = "usb"
    SERIAL = "serial"
    GPIB = "gpib"
    VXI11 = "vxi11"
    HISLIP = "hislip"


class ProtocolType(str, Enum):
    """通信协议类型枚举

    定义设备支持的通信协议。
    """

    VISA = "visa"
    SCPI = "scpi"
    MODBUS = "modbus"
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    CUSTOM = "custom"


class DeviceState(str, Enum):
    """设备状态枚举

    定义设备的生命周期状态。
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    UNKNOWN = "unknown"

    def is_connected(self) -> bool:
        """检查设备是否处于已连接状态

        Returns:
            如果设备已连接（CONNECTED, READY, BUSY）返回 True
        """
        return self in (
            DeviceState.CONNECTED,
            DeviceState.READY,
            DeviceState.BUSY,
        )

    def is_error(self) -> bool:
        """检查设备是否处于错误状态

        Returns:
            如果设备处于错误状态返回 True
        """
        return self == DeviceState.ERROR


# 导出所有公共接口
__all__ = [
    "DeviceCategory",
    "ConnectionType",
    "ProtocolType",
    "DeviceState",
]
