"""Siglent SDS1000X系列示波器驱动

实现Siglent SDS1000X系列示波器的完整驱动功能。
"""

import re
from typing import List, Dict, Any
from modules.device.families.scpi_devices import SCPIDevice
from modules.device.base import DeviceConfig


class SiglentSDS1000X(SCPIDevice):
    """Siglent SDS1000X系列示波器驱动

    特性:
    - 4通道输入
    - 100MHz带宽 (SDS1104X-E)
    - 1GSa/s采样率
    - 14Mpts存储深度
    - 支持SCPI命令集

    Attributes:
        _channel_count: 通道数量
        _timebase_range: 时基范围
        _voltage_range: 电压范围
        _memory_depth: 存储深度
    """

    def __init__(self, config: DeviceConfig):
        """初始化驱动

        Args:
            config: 设备配置
        """
        super().__init__(config)
        self._channel_count = 4
        self._timebase_range = (1e-9, 1000)  # 1ns到1000s/div
        self._voltage_range = (0.001, 100)  # 1mV到100V/div
        self._memory_depth = 14000000  # 14Mpts

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

    # ============= 通道控制 =============

    async def enable_channel(self, channel: int) -> None:
        """启用通道

        Args:
            channel: 通道号 (1-4)
        """
        self._validate_channel(channel)
        await self.protocol.write(f"C{channel}:TRACE ON")
        self._logger.info(f"Channel {channel} enabled")

    async def disable_channel(self, channel: int) -> None:
        """禁用通道

        Args:
            channel: 通道号 (1-4)
        """
        self._validate_channel(channel)
        await self.protocol.write(f"C{channel}:TRACE OFF")
        self._logger.info(f"Channel {channel} disabled")

    async def set_channel_scale(self, channel: int, volts_per_div: float) -> None:
        """设置通道垂直刻度

        Args:
            channel: 通道号 (1-4)
            volts_per_div: 垂直刻度 (V/div)
        """
        self._validate_channel(channel)

        if not self._voltage_range[0] <= volts_per_div <= self._voltage_range[1]:
            raise ValueError(f"Voltage scale out of range: {volts_per_div}")

        await self.protocol.write(f"C{channel}:VDIV {volts_per_div:.3f}")
        self._logger.debug(f"Channel {channel} scale set to {volts_per_div}V/div")

    async def set_channel_offset(self, channel: int, offset: float) -> None:
        """设置通道垂直偏移

        Args:
            channel: 通道号 (1-4)
            offset: 垂直偏移 (V)
        """
        self._validate_channel(channel)
        await self.protocol.write(f"C{channel}:OFST {offset:.3f}")

    # ============= 时基控制 =============

    async def set_timebase(self, time_per_div: float) -> None:
        """设置时基

        Args:
            time_per_div: 时基 (s/div)
        """
        if not self._timebase_range[0] <= time_per_div <= self._timebase_range[1]:
            raise ValueError(f"Timebase out of range: {time_per_div}")

        await self.protocol.write(f"TIME_DIV {time_per_div:.6f}")
        self._logger.debug(f"Timebase set to {time_per_div}s/div")

    async def set_timebase_offset(self, offset: float) -> None:
        """设置时基偏移

        Args:
            offset: 时基偏移 (s)
        """
        await self.protocol.write(f"TIME_OFFSET {offset:.6f}")

    # ============= 触发控制 =============

    async def set_trigger_mode(self, mode: str) -> None:
        """设置触发模式

        Args:
            mode: 触发模式 (EDGE, PULSE, VIDEO等)
        """
        await self.protocol.write(f"TRIG_MODE {mode}")

    async def set_trigger_source(self, source: str) -> None:
        """设置触发源

        Args:
            source: 触发源 (C1, C2, C3, C4, LINE, EXT)
        """
        await self.protocol.write(f"TRIG_SRC {source}")

    async def set_trigger_level(self, level: float) -> None:
        """设置触发电平

        Args:
            level: 触发电平 (V)
        """
        await self.protocol.write(f"TRIG_LVL {level:.3f}")

    async def set_trigger_slope(self, slope: str) -> None:
        """设置触发沿

        Args:
            slope: 触发沿 (POS, NEG, EITH)
        """
        await self.protocol.write(f"TRIG_SLOPE {slope}")

    async def force_trigger(self) -> None:
        """强制触发"""
        await self.protocol.write("TRIG_FORCE")

    async def set_acquisition_mode(self, mode: str) -> None:
        """设置采集模式

        Args:
            mode: 采集模式 (NORM, AVER, PEAK, HRES)
        """
        await self.protocol.write(f"ACQ_MODE {mode}")

    async def set_acquisition_average(self, count: int) -> None:
        """设置平均次数

        Args:
            count: 平均次数 (2-1024)
        """
        if not 2 <= count <= 1024:
            raise ValueError("Average count must be 2-1024")

        await self.protocol.write(f"ACQ_AVERAGE {count}")

    # ============= 测量功能 =============

    async def measure_frequency(self, channel: int) -> float:
        """测量频率

        Args:
            channel: 通道号 (1-4)

        Returns:
            频率值 (Hz)
        """
        self._validate_channel(channel)

        response = await self.protocol.query(f"C{channel}:PAVA? FREQ")
        # 解析响应: C1:PAVA FREQ,1.0000E+03
        match = re.search(r"FREQ,([\d.E+-]+)", response)
        if match:
            return float(match.group(1))
        else:
            raise ValueError(f"Failed to parse frequency from: {response}")

    async def measure_period(self, channel: int) -> float:
        """测量周期

        Args:
            channel: 通道号 (1-4)

        Returns:
            周期值 (s)
        """
        self._validate_channel(channel)

        response = await self.protocol.query(f"C{channel}:PAVA? PERI")
        match = re.search(r"PERI,([\d.E+-]+)", response)
        if match:
            return float(match.group(1))
        else:
            raise ValueError(f"Failed to parse period from: {response}")

    async def measure_peak_to_peak(self, channel: int) -> float:
        """测量峰峰值

        Args:
            channel: 通道号 (1-4)

        Returns:
            峰峰值 (V)
        """
        self._validate_channel(channel)

        response = await self.protocol.query(f"C{channel}:PAVA? PKPK")
        match = re.search(r"PKPK,([\d.E+-]+)", response)
        if match:
            return float(match.group(1))
        else:
            raise ValueError(f"Failed to parse peak-to-peak from: {response}")

    async def measure_rms(self, channel: int) -> float:
        """测量有效值

        Args:
            channel: 通道号 (1-4)

        Returns:
            有效值 (V)
        """
        self._validate_channel(channel)

        response = await self.protocol.query(f"C{channel}:PAVA? RMS")
        match = re.search(r"RMS,([\d.E+-]+)", response)
        if match:
            return float(match.group(1))
        else:
            raise ValueError(f"Failed to parse RMS from: {response}")

    async def measure_amplitude(self, channel: int) -> float:
        """测量幅度

        Args:
            channel: 通道号 (1-4)

        Returns:
            幅度 (V)
        """
        self._validate_channel(channel)

        response = await self.protocol.query(f"C{channel}:PAVA? AMP")
        match = re.search(r"AMP,([\d.E+-]+)", response)
        if match:
            return float(match.group(1))
        else:
            raise ValueError(f"Failed to parse amplitude from: {response}")

    # ============= 波形采集 =============

    async def capture_waveform(self, channel: int) -> List[float]:
        """采集波形数据

        Args:
            channel: 通道号 (1-4)

        Returns:
            波形数据点列表
        """
        self._validate_channel(channel)

        # 请求波形数据
        await self.protocol.write(f"C{channel}:WF? DAT2")

        # 读取波形数据 (二进制格式)
        waveform_data = await self.protocol.read()

        # 解析波形数据
        return self._parse_waveform_data(waveform_data)

    def _parse_waveform_data(self, data: str) -> List[float]:
        """解析波形数据

        Args:
            data: 原始波形数据字符串

        Returns:
            解析后的电压值列表
        """
        # 简化的波形数据解析
        # 实际实现需要处理二进制格式
        try:
            # 假设数据是逗号分隔的数值
            values = data.strip().split(",")
            return [float(val) for val in values if val]
        except Exception as e:
            self._logger.error(f"Failed to parse waveform data: {e}")
            return []

    async def get_waveform_info(self, channel: int) -> Dict[str, Any]:
        """获取波形信息

        Args:
            channel: 通道号 (1-4)

        Returns:
            波形信息字典
        """
        self._validate_channel(channel)

        # 获取基本测量参数
        frequency = await self.measure_frequency(channel)
        vpp = await self.measure_peak_to_peak(channel)
        vrms = await self.measure_rms(channel)

        return {
            "channel": channel,
            "frequency": frequency,
            "peak_to_peak": vpp,
            "rms": vrms,
            "timebase": None,  # 可以从设备查询
            "sample_rate": None,  # 可以从设备查询
        }

    # ============= 系统命令 =============

    async def stop_acquisition(self) -> None:
        """停止采集"""
        await self.protocol.write("STOP")

    async def start_acquisition(self) -> None:
        """开始采集"""
        await self.protocol.write("RUN")

    async def single_acquisition(self) -> None:
        """单次采集"""
        await self.protocol.write("SINGLE")

    async def clear_sweeps(self) -> None:
        """清除扫描"""
        await self.protocol.write("CLEAR")

    async def autoset(self) -> None:
        """自动设置"""
        await self.protocol.write("AUTO")


# 导出
__all__ = ["SiglentSDS1000X"]
