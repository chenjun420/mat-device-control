"""Tests for DeviceController"""

import pytest
from unittest.mock import patch, AsyncMock
from modules.device.controller import DeviceController, get_controller, reset_controller
from modules.device.enums import (
    DeviceCategory,
    ConnectionType,
    ProtocolType,
    DeviceState,
)


@pytest.fixture
def controller():
    """控制器实例"""
    reset_controller()
    return DeviceController()


@pytest.fixture
def psu_config():
    """电源设备配置"""
    return {
        "device_id": "psu001",
        "model": "E36312A",
        "manufacturer": "Keysight",
        "category": DeviceCategory.POWER_SUPPLY.value,
        "connection_type": ConnectionType.TCPIP.value,
        "protocol": ProtocolType.SCPI.value,
        "resource_string": "TCPIP0::192.168.1.100::5025::SOCKET",
    }


@pytest.fixture
def scope_config():
    """示波器设备配置"""
    return {
        "device_id": "scope001",
        "model": "SDS1104X-E",
        "manufacturer": "Siglent",
        "category": DeviceCategory.OSCILLOSCOPE.value,
        "connection_type": ConnectionType.TCPIP.value,
        "protocol": ProtocolType.SCPI.value,
        "resource_string": "TCPIP0::192.168.1.101::5025::SOCKET",
    }


class TestDeviceLifecycle:
    """设备生命周期测试"""

    @pytest.mark.asyncio
    async def test_create_device(self, controller, psu_config):
        """测试创建设备"""
        driver = await controller.create("psu001", psu_config)

        assert driver is not None
        assert controller.exists("psu001") is True
        assert controller.count() == 1

    @pytest.mark.asyncio
    async def test_create_device_already_exists(self, controller, psu_config):
        """测试创建已存在的设备"""
        await controller.create("psu001", psu_config)

        with pytest.raises(ValueError, match="already exists"):
            await controller.create("psu001", psu_config)

    @pytest.mark.asyncio
    async def test_create_many_devices(self, controller, psu_config, scope_config):
        """测试批量创建设备"""
        configs = [psu_config, scope_config]
        device_ids = await controller.create_many(configs)

        assert len(device_ids) == 2
        assert "psu001" in device_ids
        assert "scope001" in device_ids
        assert controller.count() == 2

    @pytest.mark.asyncio
    async def test_remove_device(self, controller, psu_config):
        """测试移除设备"""
        await controller.create("psu001", psu_config)

        result = await controller.remove("psu001")

        assert result is True
        assert controller.exists("psu001") is False
        assert controller.count() == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_device(self, controller):
        """测试移除不存在的设备"""
        result = await controller.remove("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_all_devices(self, controller, psu_config, scope_config):
        """测试清除所有设备"""
        await controller.create("psu001", psu_config)
        await controller.create("scope001", scope_config)

        await controller.clear()

        assert controller.count() == 0


class TestConnectionManagement:
    """连接管理测试"""

    @pytest.mark.asyncio
    async def test_connect_device(self, controller, psu_config):
        """测试连接设备"""
        await controller.create("psu001", psu_config)

        with (
            patch.object(
                controller._devices["psu001"].protocol,
                "_connect_tcpip",
                return_value=True,
            ),
            patch.object(
                controller._devices["psu001"].protocol,
                "query",
                return_value="Keysight,E36312A,SN12345,V1.0",
            ),
        ):
            result = await controller.connect("psu001")
            assert result is True

    @pytest.mark.asyncio
    async def test_connect_nonexistent_device(self, controller):
        """测试连接不存在的设备"""
        with pytest.raises(KeyError, match="not found"):
            await controller.connect("nonexistent")

    @pytest.mark.asyncio
    async def test_disconnect_device(self, controller, psu_config):
        """测试断开设备"""
        await controller.create("psu001", psu_config)

        with (
            patch.object(
                controller._devices["psu001"].protocol,
                "_connect_tcpip",
                return_value=True,
            ),
            patch.object(
                controller._devices["psu001"].protocol,
                "query",
                return_value="Keysight,E36312A,SN12345,V1.0",
            ),
            patch.object(controller._devices["psu001"].protocol, "disconnect"),
        ):
            await controller.connect("psu001")
            await controller.disconnect("psu001")


class TestUnifiedMethodCall:
    """统一方法调用测试"""

    @pytest.mark.asyncio
    async def test_call_method(self, controller, psu_config):
        """测试调用设备方法"""
        await controller.create("psu001", psu_config)

        with patch.object(
            controller._devices["psu001"],
            "measure_voltage",
            new_callable=AsyncMock,
            return_value=12.5,
        ):
            result = await controller.call("psu001", "measure_voltage", channel=1)
            assert result == 12.5

    @pytest.mark.asyncio
    async def test_call_nonexistent_device(self, controller):
        """测试调用不存在设备的方法"""
        with pytest.raises(KeyError, match="not found"):
            await controller.call("nonexistent", "measure_voltage")

    @pytest.mark.asyncio
    async def test_call_nonexistent_method(self, controller, psu_config):
        """测试调用不存在的方法"""
        await controller.create("psu001", psu_config)

        with pytest.raises(AttributeError, match="has no method"):
            await controller.call("psu001", "nonexistent_method")

    @pytest.mark.asyncio
    async def test_query_method(self, controller, psu_config):
        """测试查询方法"""
        await controller.create("psu001", psu_config)

        with patch.object(
            controller._devices["psu001"],
            "query",
            new_callable=AsyncMock,
            return_value="+12.5",
        ):
            result = await controller.query("psu001", "*IDN?")
            assert result == "+12.5"

    @pytest.mark.asyncio
    async def test_write_method(self, controller, psu_config):
        """测试写入方法"""
        await controller.create("psu001", psu_config)

        with patch.object(
            controller._devices["psu001"], "write", new_callable=AsyncMock
        ):
            await controller.write("psu001", "*RST")


class TestDeviceInfo:
    """设备信息测试"""

    @pytest.mark.asyncio
    async def test_get_device(self, controller, psu_config):
        """测试获取设备驱动"""
        driver = await controller.create("psu001", psu_config)

        result = controller.get("psu001")
        assert result is driver

    @pytest.mark.asyncio
    async def test_get_nonexistent_device(self, controller):
        """测试获取不存在的设备"""
        result = controller.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_device_info(self, controller, psu_config):
        """测试获取设备信息"""
        await controller.create("psu001", psu_config)

        info = controller.info("psu001")

        assert info is not None
        assert info["device_id"] == "psu001"
        assert info["model"] == "E36312A"
        assert info["manufacturer"] == "Keysight"
        assert info["category"] == DeviceCategory.POWER_SUPPLY.value

    @pytest.mark.asyncio
    async def test_list_devices(self, controller, psu_config, scope_config):
        """测试列出设备"""
        await controller.create("psu001", psu_config)
        await controller.create("scope001", scope_config)

        device_ids = controller.list()
        assert len(device_ids) == 2
        assert "psu001" in device_ids
        assert "scope001" in device_ids

    @pytest.mark.asyncio
    async def test_list_devices_by_category(self, controller, psu_config, scope_config):
        """测试按类别列出设备"""
        await controller.create("psu001", psu_config)
        await controller.create("scope001", scope_config)

        psu_ids = controller.list(category=DeviceCategory.POWER_SUPPLY)
        assert len(psu_ids) == 1
        assert "psu001" in psu_ids

        scope_ids = controller.list(category=DeviceCategory.OSCILLOSCOPE)
        assert len(scope_ids) == 1
        assert "scope001" in scope_ids

    @pytest.mark.asyncio
    async def test_list_all(self, controller, psu_config, scope_config):
        """测试列出所有设备详情"""
        await controller.create("psu001", psu_config)
        await controller.create("scope001", scope_config)

        all_info = controller.list_all()
        assert len(all_info) == 2

    @pytest.mark.asyncio
    async def test_device_state(self, controller, psu_config):
        """测试获取设备状态"""
        await controller.create("psu001", psu_config)

        state = controller.state("psu001")
        assert state == DeviceState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_is_connected(self, controller, psu_config):
        """测试检查连接状态"""
        await controller.create("psu001", psu_config)

        assert controller.is_connected("psu001") is False

    @pytest.mark.asyncio
    async def test_count(self, controller, psu_config, scope_config):
        """测试设备计数"""
        assert controller.count() == 0

        await controller.create("psu001", psu_config)
        assert controller.count() == 1

        await controller.create("scope001", scope_config)
        assert controller.count() == 2


class TestMethodIntrospection:
    """方法内省测试"""

    @pytest.mark.asyncio
    async def test_methods_returns_dict(self, controller, psu_config):
        """测试 methods() 返回字典"""
        await controller.create("psu001", psu_config)

        result = controller.methods("psu001")

        assert result is not None
        assert "device_id" in result
        assert "methods" in result
        assert isinstance(result["methods"], dict)

    @pytest.mark.asyncio
    async def test_methods_contains_expected_methods(self, controller, psu_config):
        """测试 methods() 包含预期方法"""
        await controller.create("psu001", psu_config)

        result = controller.methods("psu001")
        methods = result["methods"]

        # 验证电源设备的预期方法
        assert "set_voltage" in methods
        assert "set_current" in methods
        assert "measure_voltage" in methods
        assert "measure_current" in methods
        assert "enable_output" in methods
        assert "disable_output" in methods
        assert "reset" in methods

    @pytest.mark.asyncio
    async def test_methods_has_parameters(self, controller, psu_config):
        """测试方法参数信息"""
        await controller.create("psu001", psu_config)

        result = controller.methods("psu001")
        set_voltage = result["methods"]["set_voltage"]

        assert "parameters" in set_voltage
        assert len(set_voltage["parameters"]) >= 2  # channel, voltage

        # 检查参数结构
        param_names = [p["name"] for p in set_voltage["parameters"]]
        assert "channel" in param_names
        assert "voltage" in param_names

    @pytest.mark.asyncio
    async def test_methods_has_description(self, controller, psu_config):
        """测试方法包含描述"""
        await controller.create("psu001", psu_config)

        result = controller.methods("psu001")
        set_voltage = result["methods"]["set_voltage"]

        assert "description" in set_voltage
        assert len(set_voltage["description"]) > 0

    @pytest.mark.asyncio
    async def test_methods_nonexistent_device(self, controller):
        """测试查询不存在设备的方法"""
        result = controller.methods("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_method_names_returns_list(self, controller, psu_config):
        """测试 method_names() 返回列表"""
        await controller.create("psu001", psu_config)

        names = controller.method_names("psu001")

        assert names is not None
        assert isinstance(names, list)
        assert len(names) > 0
        assert "set_voltage" in names

    @pytest.mark.asyncio
    async def test_method_names_sorted(self, controller, psu_config):
        """测试 method_names() 返回排序列表"""
        await controller.create("psu001", psu_config)

        names = controller.method_names("psu001")

        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_method_names_nonexistent_device(self, controller):
        """测试查询不存在设备的方法名"""
        result = controller.method_names("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_has_method_true(self, controller, psu_config):
        """测试 has_method() 返回 True"""
        await controller.create("psu001", psu_config)

        assert controller.has_method("psu001", "set_voltage") is True
        assert controller.has_method("psu001", "measure_voltage") is True

    @pytest.mark.asyncio
    async def test_has_method_false(self, controller, psu_config):
        """测试 has_method() 返回 False"""
        await controller.create("psu001", psu_config)

        assert controller.has_method("psu001", "nonexistent_method") is False
        assert controller.has_method("psu001", "_private_method") is False

    @pytest.mark.asyncio
    async def test_has_method_nonexistent_device(self, controller):
        """测试检查不存在设备的方法"""
        assert controller.has_method("nonexistent", "any_method") is False

    @pytest.mark.asyncio
    async def test_methods_different_device_types(
        self, controller, psu_config, scope_config
    ):
        """测试不同设备类型有不同的方法"""
        await controller.create("psu001", psu_config)
        await controller.create("scope001", scope_config)

        psu_methods = controller.method_names("psu001")
        scope_methods = controller.method_names("scope001")

        # 电源设备应该有 set_voltage
        assert "set_voltage" in psu_methods

        # 示波器设备应该有 measure_frequency
        assert "measure_frequency" in scope_methods

        # 电源不应该有示波器的方法
        assert "measure_frequency" not in psu_methods

        # 示波器不应该有电源的方法
        assert "set_voltage" not in scope_methods


class TestGlobalController:
    """全局控制器测试"""

    def test_get_controller_lazy_init(self):
        """测试延迟初始化"""
        reset_controller()

        controller1 = get_controller()
        controller2 = get_controller()

        assert controller1 is controller2

    def test_reset_controller(self):
        """测试重置控制器"""
        controller1 = get_controller()
        reset_controller()
        controller2 = get_controller()

        assert controller1 is not controller2
