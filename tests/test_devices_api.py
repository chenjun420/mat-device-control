"""设备操作 API 单元测试

覆盖 `POST /devices/{device_id}/call` 反射式端点：
- 白名单内方法调用成功
- 白名单外方法 / 敏感方法被拒绝
- 设备不存在、参数错误、调用异常的错误路径
- method 白名单可通过环境变量与配置文件扩展
"""

import logging
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from main import app
from modules.device.controller import get_controller, reset_controller


@pytest.fixture(autouse=True)
def _stable_controller_log_level() -> Any:
    """将设备控制器日志级别固定在 INFO，保证用例隔离。

    已知缺陷（不在本任务范围，已上报）：
        ``modules/device/controller.py`` 的 ``call()`` 使用
        ``extra={"args": ...}``，而 ``args`` 是 ``LogRecord`` 的保留字段；
        仅在 DEBUG 级别下才会构造该日志记录并抛 ``KeyError``。
        其他测试可能把根日志器设为 DEBUG，故这里固定控制器日志器级别。
    """
    controller_logger = logging.getLogger("modules.device.controller")
    previous_level = controller_logger.level
    controller_logger.setLevel(logging.INFO)
    try:
        yield
    finally:
        controller_logger.setLevel(previous_level)


class StubDriver:
    """测试用设备驱动桩

    仅实现被白名单覆盖的异步方法，无需真实连接。
    """

    def __init__(self) -> None:
        self.history: list[tuple[Any, ...]] = []
        self.connected = False

    async def set_voltage(self, channel: int, voltage: float) -> dict[str, Any]:
        """设置电压"""
        self.history.append(("set_voltage", channel, voltage))
        return {"channel": channel, "voltage": voltage}

    async def measure_voltage(self, channel: int = 1) -> float:
        """测量电压"""
        self.history.append(("measure_voltage", channel))
        return 12.5

    async def reset(self) -> None:
        """复位设备"""
        self.history.append(("reset",))
        return None

    async def connect(self) -> bool:
        """连接设备"""
        self.connected = True
        self.history.append(("connect",))
        return True

    async def disconnect(self) -> None:
        """断开设备"""
        self.connected = False
        self.history.append(("disconnect",))
        return None

    async def custom_op(self, value: int) -> int:
        """自定义方法（仅用于白名单扩展测试）"""
        self.history.append(("custom_op", value))
        return value * 2

    async def file_op(self, value: int) -> int:
        """自定义方法（仅用于配置文件白名单测试）"""
        self.history.append(("file_op", value))
        return value + 1


@pytest.fixture
def stub_driver() -> StubDriver:
    """注册到全局控制器的桩驱动"""
    reset_controller()
    stub = StubDriver()
    controller = get_controller()
    # 直接注入桩驱动，绕过工厂与真实协议连接
    controller._devices["psu001"] = stub  # type: ignore[assignment]
    yield stub
    reset_controller()


@pytest.fixture
def client(stub_driver: StubDriver) -> TestClient:
    """带桩设备的同步测试客户端"""
    return TestClient(app)


def _call(client: TestClient, device_id: str, method: str, **kwargs: Any):
    """构造一次调用请求"""
    return client.post(
        f"/devices/{device_id}/call",
        json={"method": method, "kwargs": kwargs},
    )


class TestCallSuccess:
    """白名单内方法调用成功路径"""

    def test_call_allowlisted_method_success(self, client):
        """调用白名单内方法返回 200 与结果"""
        response = _call(client, "psu001", "set_voltage", channel=1, voltage=220.0)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["code"] == 200
        assert body["data"]["result"] == {"channel": 1, "voltage": 220.0}
        assert body["data"]["error"] is None

    def test_call_measure_returns_value(self, client):
        """调用 measure_voltage 返回数值"""
        response = _call(client, "psu001", "measure_voltage", channel=2)

        body = response.json()
        assert body["code"] == 200
        assert body["data"]["result"] == 12.5

    def test_response_has_result_and_error_fields(self, client):
        """响应体包含 result 与 error 两个字段"""
        response = _call(client, "psu001", "reset")

        body = response.json()
        assert "result" in body["data"]
        assert "error" in body["data"]
        assert body["data"]["result"] is None  # reset 返回 None
        assert body["data"]["error"] is None

    def test_connect_and_disconnect(self, client, stub_driver):
        """通过白名单调用 connect / disconnect"""
        assert _call(client, "psu001", "connect").json()["code"] == 200
        assert stub_driver.connected is True
        assert _call(client, "psu001", "disconnect").json()["code"] == 200
        assert stub_driver.connected is False


class TestMethodWhitelist:
    """method 白名单约束"""

    def test_method_not_in_allowlist_rejected(self, client):
        """白名单外方法返回 400"""
        response = _call(client, "psu001", "delete_everything")

        body = response.json()
        assert response.status_code == 200
        assert body["success"] is False
        assert body["code"] == 400
        assert "白名单" in body["message"]

    def test_dunder_method_rejected(self, client):
        """`__init__` 等敏感方法返回 400（非法方法名）"""
        response = _call(client, "psu001", "__init__")

        body = response.json()
        assert body["code"] == 400
        assert "非法方法名" in body["message"]

    def test_single_underscore_method_rejected(self, client):
        """单下划线私有方法同样被拒绝"""
        response = _call(client, "psu001", "_internal")

        body = response.json()
        assert body["code"] == 400
        assert "非法方法名" in body["message"]

    def test_empty_method_rejected(self, client):
        """空方法名返回 400"""
        response = _call(client, "psu001", "")

        assert response.json()["code"] == 400


class TestErrorPaths:
    """错误路径"""

    def test_device_not_found_returns_404(self, client):
        """device_id 不存在返回 404"""
        response = _call(client, "no_such_device", "reset")

        body = response.json()
        assert body["success"] is False
        assert body["code"] == 404
        assert "不存在" in body["message"]

    def test_call_exception_returns_500(self, client):
        """方法执行异常返回 500（缺少必需参数触发 TypeError）"""
        response = _call(client, "psu001", "set_voltage")  # 缺少 channel/voltage

        body = response.json()
        assert body["code"] == 500
        assert response.status_code == 200

    def test_kwargs_wrong_type_returns_400_or_500(self, client):
        """kwargs 携带未知键 → 方法签名不匹配 → 400/500"""
        response = _call(
            client, "psu001", "set_voltage", channel=1, voltage=1.0, bogus=2
        )

        assert response.json()["code"] in (400, 500)

    def test_missing_body_field_returns_422(self, client):
        """缺少必需字段 kwargs → 422 参数校验失败"""
        response = client.post(
            "/devices/psu001/call", json={"method": "reset"}
        )

        assert response.json()["code"] == 422


class TestStatelessSequential:
    """顺序调用无状态"""

    def test_sequential_calls_do_not_interfere(self, client, stub_driver):
        """多个方法顺序调用互不影响"""
        first = _call(client, "psu001", "measure_voltage").json()
        second = _call(client, "psu001", "set_voltage", channel=1, voltage=5.0).json()
        third = _call(client, "psu001", "measure_voltage").json()

        assert first["data"]["result"] == 12.5
        assert second["data"]["result"] == {"channel": 1, "voltage": 5.0}
        assert third["data"]["result"] == 12.5
        # 三次调用均被驱动记录
        assert len(stub_driver.history) == 3


class TestAllowlistConfigurable:
    """method 白名单可配置"""

    def test_env_var_extends_allowlist(self, client, monkeypatch):
        """环境变量可扩展白名单，使自定义方法可调用"""
        # 未配置时被拒绝
        assert _call(client, "psu001", "custom_op", value=21).json()["code"] == 400

        monkeypatch.setenv("MAT_DEVICE_METHOD_ALLOWLIST", "custom_op")
        response = _call(client, "psu001", "custom_op", value=21)

        body = response.json()
        assert body["code"] == 200
        assert body["data"]["result"] == 42

    def test_config_file_extends_allowlist(self, client, monkeypatch, tmp_path: Path):
        """devices.toml 的 allowed_methods 可扩展白名单"""
        config_file = tmp_path / "devices.toml"
        config_file.write_text(
            "[api]\nallowed_methods = [\"file_op\"]\n", encoding="utf-8"
        )
        monkeypatch.setenv("MAT_DEVICE_CONFIG_FILE", str(config_file))

        response = _call(client, "psu001", "file_op", value=41)

        body = response.json()
        assert body["code"] == 200
        assert body["data"]["result"] == 42

    def test_base_allowlist_always_active(self):
        """基础白名单始终生效，不受配置影响"""
        from modules.api.routes.devices import get_method_allowlist

        allowlist = get_method_allowlist()
        assert "set_voltage" in allowlist
        assert "measure_voltage" in allowlist
        assert "__init__" not in allowlist


class TestCallDeviceMethodUnit:
    """直接单元测试端点函数（不经 HTTP）"""

    def test_get_method_allowlist_includes_base(self):
        """get_method_allowlist 至少包含基础集合"""
        from modules.api.routes.devices import (
            METHOD_ALLOWLIST_BASE,
            get_method_allowlist,
        )

        assert METHOD_ALLOWLIST_BASE.issubset(get_method_allowlist())

    def test_call_device_method_returns_model(self, monkeypatch):
        """端点函数直接调用返回 DeviceCallResponse"""
        import asyncio

        from modules.api.routes.devices import (
            DeviceCallRequest,
            call_device_method,
        )

        reset_controller()
        controller = get_controller()
        controller._devices["psu001"] = StubDriver()  # type: ignore[assignment]

        request = DeviceCallRequest(method="measure_voltage", kwargs={"channel": 1})
        result = asyncio.run(call_device_method("psu001", request))

        assert result.result == 12.5
        assert result.error is None
        reset_controller()
