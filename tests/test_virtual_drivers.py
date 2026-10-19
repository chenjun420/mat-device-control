"""虚拟仪器驱动包测试。

覆盖：
- 9 型虚拟设备的关键方法返回值（确定性行为）；
- 虚拟连接恒成功、不打开 socket，断开为空操作；
- ``query("*IDN?")`` 身份响应；
- 经由 :class:`DeviceController` 的 create / connect / call 分发路径；
- 未注册型号创建报 ``ValueError``、未知方法 ``call`` 报 ``AttributeError``。
"""

import pytest
from modules.device.base import DeviceConfig
from modules.device.controller import DeviceController, reset_controller
from modules.device.drivers.virtual import (
    VirtualACSource,
    VirtualAging,
    VirtualDevice,
    VirtualDMM,
    VirtualELoad,
    VirtualPowerMeter,
    VirtualPSU,
    VirtualSafety,
    VirtualScope,
    VirtualThermo,
)
from modules.device.enums import ConnectionType, DeviceCategory, ProtocolType


def make_config(device_id: str, model: str, category: DeviceCategory) -> DeviceConfig:
    """构造一个虚拟设备配置（virtual 连接 + custom 协议）。

    Args:
        device_id: 设备唯一标识。
        model: 型号（如 ``VirtualPSU``）。
        category: 设备类别。

    Returns:
        DeviceConfig 实例。
    """
    return DeviceConfig(
        device_id=device_id,
        model=model,
        manufacturer="MAT",
        category=category,
        connection_type=ConnectionType.VIRTUAL,
        protocol=ProtocolType.CUSTOM,
        resource_string=f"virtual://{device_id}",
    )


#: (驱动类, 型号, 类别, device_id) —— 9 型设备的身份表。
DEVICE_TABLE = [
    (VirtualPSU, "VirtualPSU", DeviceCategory.POWER_SUPPLY, "v_psu"),
    (VirtualDMM, "VirtualDMM", DeviceCategory.MULTIMETER, "v_dmm"),
    (VirtualELoad, "VirtualELoad", DeviceCategory.ELECTRONIC_LOAD, "v_eload"),
    (VirtualScope, "VirtualScope", DeviceCategory.OSCILLOSCOPE, "v_scope"),
    (VirtualACSource, "VirtualACSource", DeviceCategory.POWER_SUPPLY, "v_ac"),
    (VirtualPowerMeter, "VirtualPowerMeter", DeviceCategory.POWER_METER, "v_pm"),
    (VirtualSafety, "VirtualSafety", DeviceCategory.GENERIC, "v_safety"),
    (VirtualThermo, "VirtualThermo", DeviceCategory.GENERIC, "v_thermo"),
    (VirtualAging, "VirtualAging", DeviceCategory.GENERIC, "v_aging"),
]


class TestVirtualConnectionAndIdentity:
    """虚拟连接语义与 ``*IDN?`` 身份。"""

    @pytest.mark.parametrize(
        "driver_cls,model,category,device_id",
        DEVICE_TABLE,
        ids=[row[1] for row in DEVICE_TABLE],
    )
    async def test_connect_succeeds_without_socket(
        self, driver_cls: type[VirtualDevice], model: str,
        category: DeviceCategory, device_id: str,
    ) -> None:
        """连接恒成功、无 socket；断开后状态复位。"""
        driver = driver_cls(make_config(device_id, model, category))

        assert await driver.connect() is True
        assert driver.is_connected is True

        await driver.disconnect()
        assert driver.is_connected is False

    @pytest.mark.parametrize(
        "driver_cls,model,category,device_id",
        DEVICE_TABLE,
        ids=[row[1] for row in DEVICE_TABLE],
    )
    async def test_query_idn(
        self, driver_cls: type[VirtualDevice], model: str,
        category: DeviceCategory, device_id: str,
    ) -> None:
        """``query("*IDN?")`` 返回 ``MAT,<model>,SN-V001,1.0``。"""
        driver = driver_cls(make_config(device_id, model, category))
        await driver.connect()

        assert await driver.query("*IDN?") == f"MAT,{model},SN-V001,1.0"

    async def test_device_info_is_deterministic(self) -> None:
        """设备信息为确定性身份（MAT / SN-V001 / 1.0）。"""
        driver = VirtualPSU(
            make_config("v_psu", "VirtualPSU", DeviceCategory.POWER_SUPPLY)
        )
        info = await driver.get_device_info()

        assert info.manufacturer == "MAT"
        assert info.model == "VirtualPSU"
        assert info.serial_number == "SN-V001"
        assert info.firmware_version == "1.0"


class TestVirtualPSU:
    """VirtualPSU 行为。"""

    async def test_defaults_and_set(self) -> None:
        """默认 54.0V；set 后 measure 返回最近设定值。"""
        driver = VirtualPSU(
            make_config("v_psu", "VirtualPSU", DeviceCategory.POWER_SUPPLY)
        )

        assert await driver.measure_voltage() == pytest.approx(54.0)
        assert await driver.measure_current() == pytest.approx(5.0)
        assert await driver.measure_output() == (54.0, 5.0)

        await driver.set_voltage(12.0)
        assert await driver.measure_voltage() == pytest.approx(12.0)
        assert await driver.measure_output() == (12.0, 5.0)

    async def test_enable_output_and_channel(self) -> None:
        """enable_output 与显式通道号可用。"""
        driver = VirtualPSU(
            make_config("v_psu", "VirtualPSU", DeviceCategory.POWER_SUPPLY)
        )
        await driver.enable_output(True, channel=1)
        await driver.set_voltage(7.5, channel=2)

        assert await driver.measure_voltage(channel=2) == pytest.approx(7.5)

    async def test_invalid_channel_raises(self) -> None:
        """非法通道号 fail-fast。"""
        driver = VirtualPSU(
            make_config("v_psu", "VirtualPSU", DeviceCategory.POWER_SUPPLY)
        )
        with pytest.raises(ValueError, match="Channel must be"):
            await driver.measure_voltage(channel=0)


class TestVirtualDMM:
    """VirtualDMM 行为。"""

    async def test_measurements(self) -> None:
        driver = VirtualDMM(
            make_config("v_dmm", "VirtualDMM", DeviceCategory.MULTIMETER)
        )
        assert await driver.measure_voltage() == pytest.approx(54.0)
        assert await driver.measure_current() == pytest.approx(8.0)
        assert await driver.measure_cross_regulation_pct() == pytest.approx(0.59)


class TestVirtualELoad:
    """VirtualELoad 行为。"""

    async def test_set_cc_and_protection(self) -> None:
        driver = VirtualELoad(
            make_config("v_eload", "VirtualELoad", DeviceCategory.ELECTRONIC_LOAD)
        )
        await driver.set_cc(10.0)

        assert await driver.measure_ocp_trip_pct() == pytest.approx(122.0)
        assert await driver.measure_ovp_trip_pct() == pytest.approx(118.0)
        assert await driver.measure_uvp_trip_pct() == pytest.approx(85.0)
        assert await driver.measure_scp_recovery_s() == pytest.approx(2.0)


class TestVirtualScope:
    """VirtualScope 行为。"""

    async def test_measurements(self) -> None:
        driver = VirtualScope(
            make_config("v_scope", "VirtualScope", DeviceCategory.OSCILLOSCOPE)
        )
        assert await driver.capture_inrush_peak_a() == pytest.approx(42.0)
        assert await driver.measure_ripple_mvpp() == pytest.approx(42.5)
        assert await driver.measure_transient_recovery_us() == pytest.approx(320.0)
        assert await driver.measure_startup_time_ms() == pytest.approx(86.0)
        assert await driver.measure_overshoot_pct() == pytest.approx(2.22)


class TestVirtualACSource:
    """VirtualACSource 行为。"""

    async def test_output_and_measurements(self) -> None:
        driver = VirtualACSource(
            make_config("v_ac", "VirtualACSource", DeviceCategory.POWER_SUPPLY)
        )
        await driver.set_voltage(230.0, freq=60.0)
        await driver.output_on()
        await driver.output_off()

        assert await driver.measure_turn_on_delay_ms() == pytest.approx(380.0)
        assert await driver.measure_holdup_time_ms() == pytest.approx(18.5)
        assert await driver.measure_uvlo_threshold_v() == pytest.approx(82.0)


class TestVirtualPowerMeter:
    """VirtualPowerMeter 行为。"""

    async def test_measurements(self) -> None:
        driver = VirtualPowerMeter(
            make_config("v_pm", "VirtualPowerMeter", DeviceCategory.POWER_METER)
        )
        assert await driver.measure_power_factor() == pytest.approx(0.96)
        assert await driver.measure_regulation_pct() == pytest.approx(0.42)
        assert await driver.measure_efficiency_pct() == pytest.approx(89.2)


class TestVirtualSafety:
    """VirtualSafety 行为。"""

    async def test_measurements(self) -> None:
        driver = VirtualSafety(
            make_config("v_safety", "VirtualSafety", DeviceCategory.GENERIC)
        )
        assert await driver.measure_hipot_leakage_ma() == pytest.approx(1.2)
        assert await driver.measure_insulation_resistance_mohm() == pytest.approx(520.0)
        assert await driver.measure_ground_bond_resistance_ohm() == pytest.approx(0.045)
        assert await driver.measure_touch_current_ma() == pytest.approx(0.85)


class TestVirtualThermo:
    """VirtualThermo 行为。"""

    async def test_set_temperature_and_otp(self) -> None:
        driver = VirtualThermo(
            make_config("v_thermo", "VirtualThermo", DeviceCategory.GENERIC)
        )
        await driver.set_temperature_c(50.0)

        assert await driver.measure_otp_trip_c() == pytest.approx(115.0)


class TestVirtualAging:
    """VirtualAging 行为。"""

    async def test_run_burn_in(self) -> None:
        driver = VirtualAging(
            make_config("v_aging", "VirtualAging", DeviceCategory.GENERIC)
        )
        result = await driver.run_burn_in()

        assert result == {
            "hours_completed": 48.0,
            "hours_target": 48.0,
            "ambient_c": 50.0,
            "load_pct": 100.0,
            "pass": True,
        }


class TestControllerDispatch:
    """经 DeviceController 的 create / connect / call 分发路径。"""

    async def test_create_connect_call(self) -> None:
        """端到端：创建 → 连接 → 调用方法 → 查询身份。"""
        reset_controller()
        controller = DeviceController()

        await controller.create(
            "vpsu",
            {
                "device_id": "vpsu",
                "model": "VirtualPSU",
                "manufacturer": "MAT",
                "category": "power_supply",
                "connection_type": "virtual",
                "protocol": "custom",
                "resource_string": "virtual://vpsu",
            },
        )

        assert await controller.connect("vpsu") is True
        assert controller.is_connected("vpsu") is True

        assert await controller.call("vpsu", "measure_voltage") == pytest.approx(54.0)
        await controller.call("vpsu", "set_voltage", value=48.0)
        assert await controller.call("vpsu", "measure_voltage") == pytest.approx(48.0)
        assert await controller.query("vpsu", "*IDN?") == "MAT,VirtualPSU,SN-V001,1.0"
        reset_controller()

    async def test_unsupported_model_raises_value_error(self) -> None:
        """未注册型号创建报 ValueError。"""
        reset_controller()
        controller = DeviceController()

        with pytest.raises(ValueError, match="Unsupported device"):
            await controller.create(
                "nope",
                {
                    "device_id": "nope",
                    "model": "VirtualNope",
                    "manufacturer": "MAT",
                    "category": "generic",
                    "connection_type": "virtual",
                    "protocol": "custom",
                    "resource_string": "virtual://nope",
                },
            )
        reset_controller()

    async def test_unknown_method_raises_attribute_error(self) -> None:
        """未知方法 call 报 AttributeError。"""
        reset_controller()
        controller = DeviceController()
        await controller.create(
            "vpsu",
            {
                "device_id": "vpsu",
                "model": "VirtualPSU",
                "manufacturer": "MAT",
                "category": "power_supply",
                "connection_type": "virtual",
                "protocol": "custom",
                "resource_string": "virtual://vpsu",
            },
        )

        with pytest.raises(AttributeError, match="has no method"):
            await controller.call("vpsu", "does_not_exist")
        reset_controller()

    def test_all_virtual_models_registered(self) -> None:
        """9 型虚拟驱动均在工厂注册表中。"""
        from modules.device.factory import DriverFactory

        supported = DriverFactory().get_supported_devices()
        for _, model, _, _ in DEVICE_TABLE:
            assert f"MAT.{model}" in supported
