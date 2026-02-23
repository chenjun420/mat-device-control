"""设备模块

提供设备控制的核心组件：
- 设备枚举类型 (enums)
- 设备能力接口 (capabilities)
- 设备驱动基类 (base)
- 统一设备控制器 (controller)
- 驱动工厂 (factory)
- 设备加载器 (loader)
- 协议处理器 (protocols)
- 设备族 (families)
- 具体设备驱动 (drivers)

使用 DeviceController 统一访问所有设备：
    controller = get_controller()
    await controller.create("psu001", config_dict)
    await controller.connect("psu001")
    result = await controller.call("psu001", "measure_voltage", channel=1)
"""

from modules.device.base import (
    BaseDriver,
    DeviceCommandError,
    DeviceConfig,
    DeviceConnectionError,
    DeviceError,
    DeviceInfo,
    DeviceTimeoutError,
)
from modules.device.capabilities import (
    CommandInfo,
    CommandType,
    DeviceCapability,
    ElectronicLoadCapability,
    PowerMeterCapability,
    PowerSupplyCapability,
    SignalGeneratorCapability,
    SpectrumAnalyzerCapability,
)
from modules.device.controller import DeviceController, get_controller, reset_controller
from modules.device.enums import (
    ConnectionType,
    DeviceCategory,
    DeviceState,
    ProtocolType,
)

__all__ = [
    # Enums
    "DeviceCategory",
    "ConnectionType",
    "ProtocolType",
    "DeviceState",
    # Capabilities
    "CommandType",
    "CommandInfo",
    "DeviceCapability",
    "PowerSupplyCapability",
    "ElectronicLoadCapability",
    "PowerMeterCapability",
    "SignalGeneratorCapability",
    "SpectrumAnalyzerCapability",
    # Base
    "DeviceError",
    "DeviceConnectionError",
    "DeviceTimeoutError",
    "DeviceCommandError",
    "DeviceConfig",
    "DeviceInfo",
    "BaseDriver",
    # Controller
    "DeviceController",
    "get_controller",
    "reset_controller",
]
