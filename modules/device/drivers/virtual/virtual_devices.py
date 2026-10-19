"""虚拟仪器驱动实现（确定性行为模型，无硬件）。

本模块提供 9 型虚拟设备驱动，用于在没有真实硬件的条件下，让 ATEStudio 的
PA601 23 步 commissioning 计划端到端跑通。全部行为**确定性、无随机**：重复
调用返回相同结果，便于对计划结果做数值断言。

连接语义
--------
虚拟驱动忽略一切物理连接：

* ``connect()`` 恒成功，**不打开任何 socket**；
* ``disconnect()`` 为空操作。

cfg ``resource_string`` 采用 ``virtual://<id>`` 形式；``connection_type`` 使用
本仓新增的 :attr:`~modules.device.enums.ConnectionType.VIRTUAL`（``"virtual"``），
``protocol`` 使用 ``ProtocolType.CUSTOM``。

替代方案（兼容回退）
--------------------
若部署环境尚未获得 ``ConnectionType.VIRTUAL`` 枚举，可改为
``connection_type="tcpip"`` + ``protocol="custom"`` +
``resource_string="virtual://<id>"`` 的同义配置：虚拟驱动**不读取**
``connection_type``，两种写法运行行为完全一致。本包优先采用 VIRTUAL，以便在
配置层显式区分虚拟设备与真实仪器。

方法契约
--------
* ``query("*IDN?")`` 返回 ``"MAT,Virtual<X>,SN-V001,1.0"``；
* measure 方法**无必填参数**；set 方法签名见各类定义；
* 所有公共方法以 ``async`` 实现（与 :class:`SCPIDevice` 风格一致，
  ``DeviceController.call`` 兼容同步 / 异步）。
"""

from modules.device.base import BaseDriver, DeviceCommandError, DeviceConfig, DeviceInfo


class VirtualDevice(BaseDriver):
    """虚拟设备基类（无物理连接的确定性行为模型）。

    Attributes:
        _idn_model: ``*IDN?`` 响应中的型号字段（子类覆盖）。
    """

    #: ``*IDN?`` 响应里的型号名，例如 ``"VirtualPSU"``。
    _idn_model: str = "Virtual"

    def __init__(self, config: DeviceConfig):
        """初始化虚拟设备。

        Args:
            config: 设备配置（``connection_type`` 不被读取）。
        """
        super().__init__(config)
        self._last_command: str | None = None

    # ========================================================================
    # BaseDriver 抽象方法实现
    # ========================================================================

    async def _connect_impl(self) -> bool:
        """连接实现：虚拟设备恒成功，不打开任何 socket。

        Returns:
            恒为 True。
        """
        return True

    async def _disconnect_impl(self) -> None:
        """断开实现：空操作。"""
        return None

    async def _write_impl(self, command: str) -> None:
        """写入实现：记录最近一次命令，不做任何 I/O。

        Args:
            command: 命令字符串。
        """
        self._last_command = command

    async def _query_impl(self, command: str) -> str:
        """查询实现：仅支持 ``*IDN?``，其余命令 fail-fast。

        Args:
            command: 查询命令。

        Returns:
            ``*IDN?`` 的确定性身份字符串。

        Raises:
            DeviceCommandError: 查询了虚拟设备不支持的命令。
        """
        if command.strip().upper() == "*IDN?":
            return f"MAT,{self._idn_model},SN-V001,1.0"
        raise DeviceCommandError(
            f"虚拟仪器不支持查询命令: {command!r}",
            device_id=self.config.device_id,
            command=command,
        )

    async def _read_impl(self) -> str:
        """读取实现：虚拟设备无缓冲数据，返回空串。

        Returns:
            空字符串。
        """
        return ""

    async def get_device_info(self) -> DeviceInfo:
        """获取设备信息（确定性）。

        Returns:
            DeviceInfo 实例，制造商 ``MAT``、序列号 ``SN-V001``、
            固件版本 ``1.0``。
        """
        return DeviceInfo(
            device_id=self.config.device_id,
            model=self._idn_model,
            manufacturer="MAT",
            serial_number="SN-V001",
            firmware_version="1.0",
            category=self.config.category,
        )

    # ========================================================================
    # 公共校验辅助
    # ========================================================================

    def _validate_channel(self, channel: int) -> None:
        """校验通道号。

        Args:
            channel: 通道号（须为正整数）。

        Raises:
            ValueError: 通道号非法。
        """
        if channel < 1:
            raise ValueError(f"Channel must be >= 1, got {channel}")


# ============================================================================
# 9 型虚拟设备
# ============================================================================


class VirtualPSU(VirtualDevice):
    """虚拟可编程电源（默认输出 54.0V）。"""

    _idn_model = "VirtualPSU"

    #: 未设置电压时的默认测量值（伏）。
    DEFAULT_VOLTAGE = 54.0
    #: 输出的固定电流测量值（安）。
    FIXED_CURRENT = 5.0

    def __init__(self, config: DeviceConfig):
        """初始化虚拟电源。

        Args:
            config: 设备配置。
        """
        super().__init__(config)
        self._voltage = self.DEFAULT_VOLTAGE
        self._output_enabled = False

    async def set_voltage(self, value: float, channel: int = 1) -> None:
        """设置输出电压。

        Args:
            value: 目标电压（伏）。
            channel: 通道号（默认 1）。
        """
        self._validate_channel(channel)
        self._voltage = float(value)

    async def measure_voltage(self, channel: int = 1) -> float:
        """测量输出电压。

        Args:
            channel: 通道号（默认 1）。

        Returns:
            最近设置值（未设置时为 54.0）。
        """
        self._validate_channel(channel)
        return self._voltage

    async def measure_current(self, channel: int = 1) -> float:
        """测量输出电流。

        Args:
            channel: 通道号（默认 1）。

        Returns:
            固定 5.0A。
        """
        self._validate_channel(channel)
        return self.FIXED_CURRENT

    async def measure_output(self, channel: int = 1) -> tuple[float, float]:
        """测量输出（电压, 电流）。

        Args:
            channel: 通道号（默认 1）。

        Returns:
            ``(电压, 5.0)`` 元组。
        """
        self._validate_channel(channel)
        return (self._voltage, self.FIXED_CURRENT)

    async def enable_output(self, enable: bool, channel: int = 1) -> None:
        """使能 / 关闭输出。

        Args:
            enable: True 使能，False 关闭。
            channel: 通道号（默认 1）。
        """
        self._validate_channel(channel)
        self._output_enabled = bool(enable)


class VirtualDMM(VirtualDevice):
    """虚拟数字万用表。"""

    _idn_model = "VirtualDMM"

    async def measure_voltage(self, channel: int = 1) -> float:
        """测量电压。

        Args:
            channel: 通道号（默认 1）。

        Returns:
            固定 54.0V。
        """
        self._validate_channel(channel)
        return 54.0

    async def measure_current(self, channel: int = 1) -> float:
        """测量电流。

        Args:
            channel: 通道号（默认 1）。

        Returns:
            固定 8.0A。
        """
        self._validate_channel(channel)
        return 8.0

    async def measure_cross_regulation_pct(self) -> float:
        """测量交叉调整率。

        Returns:
            固定 0.59%。
        """
        return 0.59


class VirtualELoad(VirtualDevice):
    """虚拟电子负载。"""

    _idn_model = "VirtualELoad"

    def __init__(self, config: DeviceConfig):
        """初始化虚拟电子负载。

        Args:
            config: 设备配置。
        """
        super().__init__(config)
        self._cc_current = 0.0

    async def set_cc(self, current: float, channel: int = 1) -> None:
        """设置恒流（CC）值。

        Args:
            current: 目标电流（安）。
            channel: 通道号（默认 1）。
        """
        self._validate_channel(channel)
        self._cc_current = float(current)

    async def measure_ocp_trip_pct(self) -> float:
        """测量过流保护（OCP）触发百分比。

        Returns:
            固定 122.0%。
        """
        return 122.0

    async def measure_ovp_trip_pct(self) -> float:
        """测量过压保护（OVP）触发百分比。

        Returns:
            固定 118.0%。
        """
        return 118.0

    async def measure_uvp_trip_pct(self) -> float:
        """测量欠压保护（UVP）触发百分比。

        Returns:
            固定 85.0%。
        """
        return 85.0

    async def measure_scp_recovery_s(self) -> float:
        """测量短路保护（SCP）恢复时间。

        Returns:
            固定 2.0 秒。
        """
        return 2.0


class VirtualScope(VirtualDevice):
    """虚拟示波器。"""

    _idn_model = "VirtualScope"

    async def capture_inrush_peak_a(self) -> float:
        """捕获浪涌峰值电流。

        Returns:
            固定 42.0A。
        """
        return 42.0

    async def measure_ripple_mvpp(self) -> float:
        """测量纹波（峰峰值）。

        Returns:
            固定 42.5 mVpp。
        """
        return 42.5

    async def measure_transient_recovery_us(self) -> float:
        """测量瞬态恢复时间。

        Returns:
            固定 320.0 微秒。
        """
        return 320.0

    async def measure_startup_time_ms(self) -> float:
        """测量启动时间。

        Returns:
            固定 86.0 毫秒。
        """
        return 86.0

    async def measure_overshoot_pct(self) -> float:
        """测量过冲百分比。

        Returns:
            固定 2.22%。
        """
        return 2.22


class VirtualACSource(VirtualDevice):
    """虚拟交流电源。"""

    _idn_model = "VirtualACSource"

    def __init__(self, config: DeviceConfig):
        """初始化虚拟交流源。

        Args:
            config: 设备配置。
        """
        super().__init__(config)
        self._vac = 0.0
        self._freq = 50.0
        self._output_on = False

    async def set_voltage(self, vac: float, freq: float = 50.0) -> None:
        """设置交流输出电压与频率。

        Args:
            vac: 目标电压（伏）。
            freq: 频率（赫兹，默认 50.0）。
        """
        self._vac = float(vac)
        self._freq = float(freq)

    async def output_on(self) -> None:
        """打开交流输出。"""
        self._output_on = True

    async def output_off(self) -> None:
        """关闭交流输出。"""
        self._output_on = False

    async def measure_turn_on_delay_ms(self) -> float:
        """测量开机延迟。

        Returns:
            固定 380.0 毫秒。
        """
        return 380.0

    async def measure_holdup_time_ms(self) -> float:
        """测量保持时间。

        Returns:
            固定 18.5 毫秒。
        """
        return 18.5

    async def measure_uvlo_threshold_v(self) -> float:
        """测量欠压锁定（UVLO）阈值。

        Returns:
            固定 82.0V。
        """
        return 82.0


class VirtualPowerMeter(VirtualDevice):
    """虚拟功率计。"""

    _idn_model = "VirtualPowerMeter"

    async def measure_power_factor(self) -> float:
        """测量功率因数。

        Returns:
            固定 0.96。
        """
        return 0.96

    async def measure_regulation_pct(self) -> float:
        """测量调整率。

        Returns:
            固定 0.42%。
        """
        return 0.42

    async def measure_efficiency_pct(self) -> float:
        """测量效率。

        Returns:
            固定 89.2%。
        """
        return 89.2


class VirtualSafety(VirtualDevice):
    """虚拟安规测试仪。"""

    _idn_model = "VirtualSafety"

    async def measure_hipot_leakage_ma(self) -> float:
        """测量耐压（Hipot）漏电流。

        Returns:
            固定 1.2 mA。
        """
        return 1.2

    async def measure_insulation_resistance_mohm(self) -> float:
        """测量绝缘电阻。

        Returns:
            固定 520.0 MΩ。
        """
        return 520.0

    async def measure_ground_bond_resistance_ohm(self) -> float:
        """测量接地导通电阻。

        Returns:
            固定 0.045 Ω。
        """
        return 0.045

    async def measure_touch_current_ma(self) -> float:
        """测量接触电流。

        Returns:
            固定 0.85 mA。
        """
        return 0.85


class VirtualThermo(VirtualDevice):
    """虚拟温控 / 温箱。"""

    _idn_model = "VirtualThermo"

    def __init__(self, config: DeviceConfig):
        """初始化虚拟温控设备。

        Args:
            config: 设备配置。
        """
        super().__init__(config)
        self._temperature_c = 25.0

    async def set_temperature_c(self, c: float) -> None:
        """设置温度。

        Args:
            c: 目标温度（摄氏度）。
        """
        self._temperature_c = float(c)

    async def measure_otp_trip_c(self) -> float:
        """测量过温保护（OTP）触发温度。

        Returns:
            固定 115.0°C。
        """
        return 115.0


class VirtualAging(VirtualDevice):
    """虚拟老化测试设备。"""

    _idn_model = "VirtualAging"

    async def run_burn_in(self) -> dict[str, float | bool]:
        """执行老化（burn-in）测试。

        Returns:
            确定性结果字典，包含完成小时、目标小时、环境温度、
            负载百分比与通过标志。
        """
        return {
            "hours_completed": 48.0,
            "hours_target": 48.0,
            "ambient_c": 50.0,
            "load_pct": 100.0,
            "pass": True,
        }


# 导出
__all__ = [
    "VirtualDevice",
    "VirtualPSU",
    "VirtualDMM",
    "VirtualELoad",
    "VirtualScope",
    "VirtualACSource",
    "VirtualPowerMeter",
    "VirtualSafety",
    "VirtualThermo",
    "VirtualAging",
]
