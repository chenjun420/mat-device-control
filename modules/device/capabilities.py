"""设备能力接口定义

定义各类测试设备的能力接口，包括：
- 程控电源 (PowerSupply)
- 电子负载 (ElectronicLoad)
- 功率计 (PowerMeter)
- 信号发生器 (SignalGenerator)
- 频谱分析仪 (SpectrumAnalyzer)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class CommandType(str, Enum):
    """命令类型枚举"""

    READ = "read"
    WRITE = "write"
    ACTION = "action"
    QUERY = "query"


@dataclass
class CommandInfo:
    """命令信息"""

    name: str
    description: str
    command_type: CommandType
    parameters: dict[str, str] | None = None
    return_type: str | None = None
    example: str | None = None


class DeviceCapability(ABC):
    """设备能力基础接口

    所有设备能力类必须实现此接口，提供：
    - 能力列表查询
    - 命令全集查询
    - 命令验证
    """

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """获取设备支持的能力列表

        Returns:
            能力名称列表，如 ["voltage_control", "current_control"]
        """
        pass

    @abstractmethod
    def get_commands(self) -> list[CommandInfo]:
        """获取设备支持的命令全集

        Returns:
            CommandInfo 对象列表
        """
        pass

    @abstractmethod
    def validate_command(self, command: str, parameters: dict[str, Any]) -> bool:
        """验证命令和参数是否有效

        Args:
            command: 命令名称
            parameters: 命令参数字典

        Returns:
            命令和参数是否有效
        """
        pass


class PowerSupplyCapability(DeviceCapability):
    """程控电源能力接口"""

    def get_capabilities(self) -> list[str]:
        """获取能力列表"""
        return [
            "voltage_control",
            "current_control",
            "output_control",
            "measurement",
        ]

    def get_commands(self) -> list[CommandInfo]:
        """获取命令列表"""
        return [
            CommandInfo(
                "set_voltage",
                "设置输出电压",
                CommandType.WRITE,
                {"voltage": "float", "channel": "int"},
                "bool",
            ),
            CommandInfo(
                "get_voltage",
                "读取输出电压",
                CommandType.READ,
                {"channel": "int"},
                "float",
            ),
            CommandInfo(
                "set_current_limit",
                "设置电流限制",
                CommandType.WRITE,
                {"current": "float", "channel": "int"},
                "bool",
            ),
            CommandInfo(
                "get_current_limit",
                "读取电流限制",
                CommandType.READ,
                {"channel": "int"},
                "float",
            ),
            CommandInfo(
                "enable_output",
                "启用输出",
                CommandType.ACTION,
                {"channel": "int"},
                "bool",
            ),
            CommandInfo(
                "disable_output",
                "禁用输出",
                CommandType.ACTION,
                {"channel": "int"},
                "bool",
            ),
            CommandInfo(
                "is_output_enabled",
                "查询输出状态",
                CommandType.QUERY,
                {"channel": "int"},
                "bool",
            ),
        ]

    def validate_command(self, command: str, parameters: dict[str, Any]) -> bool:
        """验证命令和参数"""
        valid_commands = {cmd.name for cmd in self.get_commands()}
        if command not in valid_commands:
            return False

        # 参数验证
        if command in ["set_voltage", "set_current_limit"]:
            return "voltage" in parameters or "current" in parameters

        return True


class ElectronicLoadCapability(DeviceCapability):
    """电子负载能力接口"""

    def get_capabilities(self) -> list[str]:
        """获取能力列表"""
        return [
            "load_control",
            "mode_control",
            "measurement",
            "protection",
        ]

    def get_commands(self) -> list[CommandInfo]:
        """获取命令列表"""
        return [
            CommandInfo(
                "set_load_current",
                "设置负载电流",
                CommandType.WRITE,
                {"current": "float", "channel": "int"},
                "bool",
            ),
            CommandInfo(
                "set_load_voltage",
                "设置负载电压",
                CommandType.WRITE,
                {"voltage": "float", "channel": "int"},
                "bool",
            ),
            CommandInfo(
                "set_load_power",
                "设置负载功率",
                CommandType.WRITE,
                {"power": "float", "channel": "int"},
                "bool",
            ),
            CommandInfo(
                "get_load_value",
                "读取负载值",
                CommandType.READ,
                {"channel": "int"},
                "float",
            ),
            CommandInfo(
                "set_mode",
                "设置工作模式",
                CommandType.WRITE,
                {"mode": "str", "channel": "int"},
                "bool",
            ),
        ]

    def validate_command(self, command: str, parameters: dict[str, Any]) -> bool:
        """验证命令和参数"""
        valid_commands = {cmd.name for cmd in self.get_commands()}
        return command in valid_commands


class PowerMeterCapability(DeviceCapability):
    """功率计能力接口"""

    def get_capabilities(self) -> list[str]:
        """获取能力列表"""
        return [
            "power_measurement",
            "voltage_measurement",
            "current_measurement",
            "frequency_measurement",
        ]

    def get_commands(self) -> list[CommandInfo]:
        """获取命令列表"""
        return [
            CommandInfo(
                "measure_power",
                "测量功率",
                CommandType.READ,
                {"channel": "int"},
                "float",
            ),
            CommandInfo(
                "measure_voltage",
                "测量电压",
                CommandType.READ,
                {"channel": "int"},
                "float",
            ),
            CommandInfo(
                "measure_current",
                "测量电流",
                CommandType.READ,
                {"channel": "int"},
                "float",
            ),
            CommandInfo(
                "measure_frequency",
                "测量频率",
                CommandType.READ,
                {"channel": "int"},
                "float",
            ),
        ]

    def validate_command(self, command: str, parameters: dict[str, Any]) -> bool:
        """验证命令和参数"""
        valid_commands = {cmd.name for cmd in self.get_commands()}
        return command in valid_commands


class SignalGeneratorCapability(DeviceCapability):
    """信号发生器能力接口"""

    def get_capabilities(self) -> list[str]:
        """获取能力列表"""
        return [
            "waveform_generation",
            "frequency_control",
            "amplitude_control",
            "modulation",
        ]

    def get_commands(self) -> list[CommandInfo]:
        """获取命令列表"""
        return [
            CommandInfo(
                "set_waveform",
                "设置波形类型",
                CommandType.WRITE,
                {"waveform": "str", "channel": "int"},
                "bool",
            ),
            CommandInfo(
                "set_frequency",
                "设置频率",
                CommandType.WRITE,
                {"frequency": "float", "channel": "int"},
                "bool",
            ),
            CommandInfo(
                "set_amplitude",
                "设置幅度",
                CommandType.WRITE,
                {"amplitude": "float", "channel": "int"},
                "bool",
            ),
            CommandInfo(
                "enable_output",
                "启用输出",
                CommandType.ACTION,
                {"channel": "int"},
                "bool",
            ),
        ]

    def validate_command(self, command: str, parameters: dict[str, Any]) -> bool:
        """验证命令和参数"""
        valid_commands = {cmd.name for cmd in self.get_commands()}
        return command in valid_commands


class SpectrumAnalyzerCapability(DeviceCapability):
    """频谱分析仪能力接口"""

    def get_capabilities(self) -> list[str]:
        """获取能力列表"""
        return [
            "spectrum_analysis",
            "frequency_sweep",
            "power_measurement",
            "bandwidth_control",
        ]

    def get_commands(self) -> list[CommandInfo]:
        """获取命令列表"""
        return [
            CommandInfo(
                "set_center_frequency",
                "设置中心频率",
                CommandType.WRITE,
                {"frequency": "float"},
                "bool",
            ),
            CommandInfo(
                "set_span",
                "设置扫宽",
                CommandType.WRITE,
                {"span": "float"},
                "bool",
            ),
            CommandInfo(
                "set_resolution_bandwidth",
                "设置分辨率带宽",
                CommandType.WRITE,
                {"rbw": "float"},
                "bool",
            ),
            CommandInfo(
                "sweep_spectrum",
                "执行频谱扫描",
                CommandType.ACTION,
                {},
                "List[float]",
            ),
        ]

    def validate_command(self, command: str, parameters: dict[str, Any]) -> bool:
        """验证命令和参数"""
        valid_commands = {cmd.name for cmd in self.get_commands()}
        return command in valid_commands


# 导出所有公共接口
__all__ = [
    "CommandType",
    "CommandInfo",
    "DeviceCapability",
    "PowerSupplyCapability",
    "ElectronicLoadCapability",
    "PowerMeterCapability",
    "SignalGeneratorCapability",
    "SpectrumAnalyzerCapability",
]
