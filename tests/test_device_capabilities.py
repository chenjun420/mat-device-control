"""设备能力接口单元测试"""

import pytest

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


class TestCommandInfo:
    """CommandInfo 测试类"""

    def test_command_info_creation(self):
        """测试命令信息创建"""
        cmd = CommandInfo(
            name="set_voltage",
            description="设置输出电压",
            command_type=CommandType.WRITE,
            parameters={"voltage": "float", "channel": "int"},
            return_type="bool",
        )

        assert cmd.name == "set_voltage"
        assert cmd.description == "设置输出电压"
        assert cmd.command_type == CommandType.WRITE
        assert cmd.parameters == {"voltage": "float", "channel": "int"}
        assert cmd.return_type == "bool"

    def test_command_info_optional_fields(self):
        """测试命令信息可选字段"""
        cmd = CommandInfo(
            name="enable_output",
            description="启用输出",
            command_type=CommandType.ACTION,
        )

        assert cmd.parameters is None
        assert cmd.return_type is None
        assert cmd.example is None


class TestCommandType:
    """CommandType 测试类"""

    def test_command_types_exist(self):
        """测试命令类型枚举值"""
        assert CommandType.READ == "read"
        assert CommandType.WRITE == "write"
        assert CommandType.ACTION == "action"
        assert CommandType.QUERY == "query"


class TestPowerSupplyCapability:
    """PowerSupplyCapability 测试类"""

    def test_get_capabilities(self):
        """测试获取能力列表"""
        capability = PowerSupplyCapability()
        caps = capability.get_capabilities()

        assert "voltage_control" in caps
        assert "current_control" in caps
        assert "output_control" in caps
        assert "measurement" in caps

    def test_get_commands(self):
        """测试获取命令列表"""
        capability = PowerSupplyCapability()
        commands = capability.get_commands()

        command_names = [cmd.name for cmd in commands]
        assert "set_voltage" in command_names
        assert "get_voltage" in command_names
        assert "set_current_limit" in command_names
        assert "get_current_limit" in command_names
        assert "enable_output" in command_names
        assert "disable_output" in command_names
        assert "is_output_enabled" in command_names

    def test_validate_command_valid(self):
        """测试有效命令验证"""
        capability = PowerSupplyCapability()

        assert capability.validate_command(
            "set_voltage", {"voltage": 5.0, "channel": 1}
        )
        assert capability.validate_command(
            "set_current_limit", {"current": 1.0, "channel": 1}
        )
        assert capability.validate_command("enable_output", {"channel": 1})
        assert capability.validate_command("get_voltage", {"channel": 1})

    def test_validate_command_invalid(self):
        """测试无效命令验证"""
        capability = PowerSupplyCapability()

        assert not capability.validate_command("invalid_command", {})
        assert not capability.validate_command("set_voltage", {})  # 缺少必需参数


class TestElectronicLoadCapability:
    """ElectronicLoadCapability 测试类"""

    def test_get_capabilities(self):
        """测试获取能力列表"""
        capability = ElectronicLoadCapability()
        caps = capability.get_capabilities()

        assert "load_control" in caps
        assert "mode_control" in caps
        assert "measurement" in caps
        assert "protection" in caps

    def test_get_commands(self):
        """测试获取命令列表"""
        capability = ElectronicLoadCapability()
        commands = capability.get_commands()

        command_names = [cmd.name for cmd in commands]
        assert "set_load_current" in command_names
        assert "set_load_voltage" in command_names
        assert "set_load_power" in command_names
        assert "get_load_value" in command_names
        assert "set_mode" in command_names

    def test_validate_command(self):
        """测试命令验证"""
        capability = ElectronicLoadCapability()

        assert capability.validate_command("set_load_current", {"current": 2.0})
        assert not capability.validate_command("invalid_command", {})


class TestPowerMeterCapability:
    """PowerMeterCapability 测试类"""

    def test_get_capabilities(self):
        """测试获取能力列表"""
        capability = PowerMeterCapability()
        caps = capability.get_capabilities()

        assert "power_measurement" in caps
        assert "voltage_measurement" in caps
        assert "current_measurement" in caps
        assert "frequency_measurement" in caps

    def test_get_commands(self):
        """测试获取命令列表"""
        capability = PowerMeterCapability()
        commands = capability.get_commands()

        command_names = [cmd.name for cmd in commands]
        assert "measure_power" in command_names
        assert "measure_voltage" in command_names
        assert "measure_current" in command_names
        assert "measure_frequency" in command_names

    def test_validate_command(self):
        """测试命令验证"""
        capability = PowerMeterCapability()

        assert capability.validate_command("measure_power", {"channel": 1})
        assert not capability.validate_command("invalid_command", {})


class TestSignalGeneratorCapability:
    """SignalGeneratorCapability 测试类"""

    def test_get_capabilities(self):
        """测试获取能力列表"""
        capability = SignalGeneratorCapability()
        caps = capability.get_capabilities()

        assert "waveform_generation" in caps
        assert "frequency_control" in caps
        assert "amplitude_control" in caps
        assert "modulation" in caps

    def test_get_commands(self):
        """测试获取命令列表"""
        capability = SignalGeneratorCapability()
        commands = capability.get_commands()

        command_names = [cmd.name for cmd in commands]
        assert "set_waveform" in command_names
        assert "set_frequency" in command_names
        assert "set_amplitude" in command_names
        assert "enable_output" in command_names

    def test_validate_command(self):
        """测试命令验证"""
        capability = SignalGeneratorCapability()

        assert capability.validate_command("set_waveform", {"waveform": "sine"})
        assert not capability.validate_command("invalid_command", {})


class TestSpectrumAnalyzerCapability:
    """SpectrumAnalyzerCapability 测试类"""

    def test_get_capabilities(self):
        """测试获取能力列表"""
        capability = SpectrumAnalyzerCapability()
        caps = capability.get_capabilities()

        assert "spectrum_analysis" in caps
        assert "frequency_sweep" in caps
        assert "power_measurement" in caps
        assert "bandwidth_control" in caps

    def test_get_commands(self):
        """测试获取命令列表"""
        capability = SpectrumAnalyzerCapability()
        commands = capability.get_commands()

        command_names = [cmd.name for cmd in commands]
        assert "set_center_frequency" in command_names
        assert "set_span" in command_names
        assert "set_resolution_bandwidth" in command_names
        assert "sweep_spectrum" in command_names

    def test_validate_command(self):
        """测试命令验证"""
        capability = SpectrumAnalyzerCapability()

        assert capability.validate_command("set_center_frequency", {"frequency": 1e9})
        assert not capability.validate_command("invalid_command", {})


class TestDeviceCapabilityAbstract:
    """DeviceCapability 抽象类测试"""

    def test_cannot_instantiate_abstract(self):
        """测试不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            DeviceCapability()  # type: ignore

    def test_subclass_must_implement_methods(self):
        """测试子类必须实现所有抽象方法"""

        class IncompleteCapability(DeviceCapability):
            pass

        with pytest.raises(TypeError):
            IncompleteCapability()  # type: ignore
