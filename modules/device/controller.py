"""设备控制器

提供统一的设备访问控制接口：
- 所有设备通过 device_id 访问
- 统一的方法调用接口，不区分设备类型
- 支持动态方法调用

Usage:
    controller = DeviceController()

    # 创建设备
    await controller.create("psu001", config_dict)

    # 连接设备
    await controller.connect("psu001")

    # 调用设备方法（统一接口）
    voltage = await controller.call("psu001", "measure_voltage", channel=1)
    await controller.call("psu001", "set_voltage", channel=1, voltage=12.0)

    # 查询设备信息
    info = controller.info("psu001")

    # 查询设备方法列表
    methods = controller.methods("psu001")
"""

from typing import Any, Optional
import inspect
from modules.core.logging import get_logger
from modules.device.base import BaseDriver, DeviceConfig, DeviceInfo
from modules.device.enums import DeviceState, DeviceCategory
from modules.device.factory import get_factory

logger = get_logger(__name__)


def _is_public_async_method(obj: Any, name: str) -> bool:
    """检查是否是公共异步方法

    Args:
        obj: 对象
        name: 方法名

    Returns:
        True 如果是公共异步方法
    """
    # 排除私有方法和特殊方法
    if name.startswith("_"):
        return False

    attr = getattr(obj, name, None)
    if attr is None:
        return False

    # 检查是否是方法
    if not callable(attr):
        return False

    # 检查是否是协程函数
    return inspect.iscoroutinefunction(attr)


def _get_method_signature(method: Any) -> dict[str, Any]:
    """获取方法签名信息

    Args:
        method: 方法对象

    Returns:
        方法签名信息字典
    """
    try:
        sig = inspect.signature(method)
        params = []

        for param_name, param in sig.parameters.items():
            # 跳过 self 参数
            if param_name == "self":
                continue

            param_info = {
                "name": param_name,
                "type": str(param.annotation)
                if param.annotation != inspect.Parameter.empty
                else "Any",
                "default": str(param.default)
                if param.default != inspect.Parameter.empty
                else None,
                "required": param.default == inspect.Parameter.empty,
            }
            params.append(param_info)

        # 获取返回类型
        return_type = (
            str(sig.return_annotation)
            if sig.return_annotation != inspect.Signature.empty
            else "Any"
        )

        return {
            "parameters": params,
            "return_type": return_type,
        }
    except Exception:
        return {"parameters": [], "return_type": "Any"}


class DeviceController:
    """设备控制器

    提供统一的设备访问控制接口。所有设备通过 device_id 访问，
    不需要为不同类型设备提供不同的接口。

    Attributes:
        _devices: 设备实例字典 {device_id: driver}
        _factory: 驱动工厂实例
    """

    def __init__(self):
        """初始化设备控制器"""
        self._devices: dict[str, BaseDriver] = {}
        self._factory = get_factory()

    # ========================================================================
    # 设备生命周期管理
    # ========================================================================

    async def create(
        self, device_id: str, config: dict[str, Any] | DeviceConfig
    ) -> BaseDriver:
        """创建设备

        Args:
            device_id: 设备唯一标识符
            config: 设备配置（字典或 DeviceConfig 实例）

        Returns:
            设备驱动实例

        Raises:
            ValueError: 设备已存在或配置无效
        """
        if device_id in self._devices:
            raise ValueError(f"Device '{device_id}' already exists")

        # 转换配置
        if isinstance(config, dict):
            device_config = DeviceConfig.from_dict(config)
        else:
            device_config = config

        # 确保配置中的 device_id 与参数一致
        if device_config.device_id != device_id:
            device_config = DeviceConfig(
                device_id=device_id,
                model=device_config.model,
                manufacturer=device_config.manufacturer,
                category=device_config.category,
                connection_type=device_config.connection_type,
                protocol=device_config.protocol,
                resource_string=device_config.resource_string,
                timeout=device_config.timeout,
                retry_count=device_config.retry_count,
                retry_delay=device_config.retry_delay,
                config=device_config.config,
            )

        # 使用工厂创建驱动
        driver = self._factory.create_driver(device_config)
        self._devices[device_id] = driver

        logger.info(
            "Device created",
            extra={
                "device_id": device_id,
                "model": device_config.model,
                "manufacturer": device_config.manufacturer,
                "category": device_config.category.value,
            },
        )

        return driver

    async def create_many(self, configs: list[dict[str, Any]]) -> list[str]:
        """批量创建设备

        Args:
            configs: 设备配置列表（每个配置必须包含 device_id）

        Returns:
            创建的设备ID列表

        Raises:
            ValueError: 任何配置无效
        """
        device_ids = []
        for config in configs:
            if "device_id" not in config:
                raise ValueError("Config must contain 'device_id'")
            device_id = config["device_id"]
            await self.create(device_id, config)
            device_ids.append(device_id)
        return device_ids

    async def remove(self, device_id: str) -> bool:
        """移除设备

        自动断开连接后移除设备。

        Args:
            device_id: 设备ID

        Returns:
            True 如果成功移除，False 如果设备不存在
        """
        if device_id not in self._devices:
            return False

        driver = self._devices[device_id]

        # 自动断开连接
        if driver.is_connected:
            await driver.disconnect()

        del self._devices[device_id]
        logger.info("Device removed", extra={"device_id": device_id})
        return True

    async def clear(self) -> None:
        """清除所有设备"""
        for device_id in list(self._devices.keys()):
            await self.remove(device_id)
        logger.info("All devices cleared")

    # ========================================================================
    # 连接管理
    # ========================================================================

    async def connect(self, device_id: str) -> bool:
        """连接设备

        Args:
            device_id: 设备ID

        Returns:
            True 如果连接成功

        Raises:
            KeyError: 设备不存在
        """
        if device_id not in self._devices:
            raise KeyError(f"Device '{device_id}' not found")

        driver = self._devices[device_id]
        result = await driver.connect()

        logger.info(
            "Device connected", extra={"device_id": device_id, "success": result}
        )

        return result

    async def disconnect(self, device_id: str) -> None:
        """断开设备连接

        Args:
            device_id: 设备ID
        """
        if device_id not in self._devices:
            return

        driver = self._devices[device_id]
        await driver.disconnect()
        logger.info("Device disconnected", extra={"device_id": device_id})

    async def disconnect_all(self) -> None:
        """断开所有设备连接"""
        for device_id, driver in self._devices.items():
            if driver.is_connected:
                await driver.disconnect()
                logger.debug("Device disconnected", extra={"device_id": device_id})

    # ========================================================================
    # 统一方法调用接口
    # ========================================================================

    async def call(self, device_id: str, method: str, *args, **kwargs) -> Any:
        """调用设备方法（统一接口）

        这是访问所有设备功能的主要接口，无论设备类型如何。

        Args:
            device_id: 设备ID
            method: 方法名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            方法返回值

        Raises:
            KeyError: 设备不存在
            AttributeError: 方法不存在
            RuntimeError: 设备未连接（如果方法需要连接）

        Examples:
            # 电源设备
            await controller.call("psu001", "set_voltage", channel=1, voltage=12.0)
            voltage = await controller.call("psu001", "measure_voltage", channel=1)

            # 示波器设备
            await controller.call("scope001", "set_timebase", time_per_div=1e-3)
            freq = await controller.call("scope001", "measure_frequency", channel=1)

            # 通用方法
            await controller.call("dev001", "reset")
            error = await controller.call("dev001", "get_error")
        """
        if device_id not in self._devices:
            raise KeyError(f"Device '{device_id}' not found")

        driver = self._devices[device_id]

        # 获取方法
        if not hasattr(driver, method):
            raise AttributeError(f"Device '{device_id}' has no method '{method}'")

        method_func = getattr(driver, method)

        # 检查是否是可调用方法
        if not callable(method_func):
            raise AttributeError(
                f"'{method}' is not a callable method on device '{device_id}'"
            )

        # 调用方法
        logger.debug(
            "Calling device method",
            extra={
                "device_id": device_id,
                "method": method,
                "args": str(args)[:100] if args else None,
                "kwargs": str(kwargs)[:100] if kwargs else None,
            },
        )

        import asyncio

        result = method_func(*args, **kwargs)
        # 如果是协程则等待，否则直接返回
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def query(self, device_id: str, command: str) -> str:
        """发送查询命令（便捷方法）

        等同于 call(device_id, "query", command)

        Args:
            device_id: 设备ID
            command: SCPI 命令

        Returns:
            设备响应
        """
        return await self.call(device_id, "query", command)

    async def write(self, device_id: str, command: str) -> None:
        """发送写入命令（便捷方法）

        等同于 call(device_id, "write", command)

        Args:
            device_id: 设备ID
            command: SCPI 命令
        """
        await self.call(device_id, "write", command)

    async def read(self, device_id: str) -> str:
        """读取数据（便捷方法）

        等同于 call(device_id, "read")

        Args:
            device_id: 设备ID

        Returns:
            读取的数据
        """
        return await self.call(device_id, "read")

    # ========================================================================
    # 设备信息查询
    # ========================================================================

    def get(self, device_id: str) -> Optional[BaseDriver]:
        """获取设备驱动实例

        如果需要直接访问驱动实例，可以使用此方法。
        但推荐使用 call() 方法进行统一访问。

        Args:
            device_id: 设备ID

        Returns:
            设备驱动实例，如果不存在返回 None
        """
        return self._devices.get(device_id)

    def info(self, device_id: str) -> Optional[dict[str, Any]]:
        """获取设备信息

        Args:
            device_id: 设备ID

        Returns:
            设备信息字典，如果设备不存在返回 None
        """
        driver = self._devices.get(device_id)
        if driver is None:
            return None

        return {
            "device_id": device_id,
            "model": driver.config.model,
            "manufacturer": driver.config.manufacturer,
            "category": driver.config.category.value,
            "connection_type": driver.config.connection_type.value,
            "protocol": driver.config.protocol.value,
            "resource_string": driver.config.resource_string,
            "state": driver.state.value,
            "is_connected": driver.is_connected,
        }

    def methods(
        self, device_id: str, include_doc: bool = True
    ) -> Optional[dict[str, Any]]:
        """获取设备支持的方法列表及参数说明

        使用 Python inspect 模块动态获取设备的所有公共异步方法、
        参数签名和文档字符串。

        Args:
            device_id: 设备ID
            include_doc: 是否包含方法文档字符串

        Returns:
            方法信息字典，格式:
            {
                "device_id": "xxx",
                "methods": {
                    "method_name": {
                        "description": "方法说明",
                        "parameters": [
                            {
                                "name": "参数名",
                                "type": "参数类型",
                                "default": "默认值或None",
                                "required": True/False
                            }
                        ],
                        "return_type": "返回类型"
                    }
                }
            }
            如果设备不存在返回 None

        Example:
            methods = controller.methods("psu001")
            # methods["methods"]["set_voltage"]["parameters"]
            # [{"name": "channel", "type": "int", ...}, {"name": "voltage", ...}]
        """
        driver = self._devices.get(device_id)
        if driver is None:
            return None

        methods_info = {}

        # 遍历驱动对象的所有属性
        for name in dir(driver):
            if _is_public_async_method(driver, name):
                method = getattr(driver, name)

                # 获取方法信息
                method_info = _get_method_signature(method)

                # 添加文档字符串
                if include_doc:
                    doc = inspect.getdoc(method)
                    method_info["description"] = (
                        doc if doc else "No description available"
                    )

                methods_info[name] = method_info

        return {
            "device_id": device_id,
            "model": driver.config.model,
            "manufacturer": driver.config.manufacturer,
            "category": driver.config.category.value,
            "methods": methods_info,
        }

    def method_names(self, device_id: str) -> Optional[list[str]]:
        """获取设备支持的方法名称列表（简化版）

        Args:
            device_id: 设备ID

        Returns:
            方法名称列表，如果设备不存在返回 None
        """
        driver = self._devices.get(device_id)
        if driver is None:
            return None

        names = []
        for name in dir(driver):
            if _is_public_async_method(driver, name):
                names.append(name)

        return sorted(names)

    def has_method(self, device_id: str, method: str) -> bool:
        """检查设备是否支持某个方法

        Args:
            device_id: 设备ID
            method: 方法名称

        Returns:
            True 如果设备存在且支持该方法
        """
        driver = self._devices.get(device_id)
        if driver is None:
            return False

        return _is_public_async_method(driver, method)

    async def device_info(self, device_id: str) -> Optional[DeviceInfo]:
        """获取详细设备信息（从设备读取）

        Args:
            device_id: 设备ID

        Returns:
            DeviceInfo 实例，如果设备不存在返回 None
        """
        driver = self._devices.get(device_id)
        if driver is None:
            return None

        return await driver.get_device_info()

    def list(
        self,
        category: Optional[DeviceCategory] = None,
        connected_only: bool = False,
    ) -> list[str]:
        """列出设备ID

        Args:
            category: 可选，按类别过滤
            connected_only: 是否只返回已连接的设备

        Returns:
            设备ID列表
        """
        device_ids = []
        for device_id, driver in self._devices.items():
            # 类别过滤
            if category and driver.config.category != category:
                continue
            # 连接状态过滤
            if connected_only and not driver.is_connected:
                continue
            device_ids.append(device_id)

        return device_ids

    def list_all(self) -> list[dict[str, Any]]:
        """列出所有设备的详细信息

        Returns:
            设备信息字典列表
        """
        results = []
        for device_id in self._devices.keys():
            info = self.info(device_id)
            if info is not None:
                results.append(info)
        return results

    def state(self, device_id: str) -> Optional[DeviceState]:
        """获取设备状态

        Args:
            device_id: 设备ID

        Returns:
            设备状态，如果设备不存在返回 None
        """
        driver = self._devices.get(device_id)
        return driver.state if driver else None

    def exists(self, device_id: str) -> bool:
        """检查设备是否存在

        Args:
            device_id: 设备ID

        Returns:
            True 如果设备存在
        """
        return device_id in self._devices

    def is_connected(self, device_id: str) -> bool:
        """检查设备是否已连接

        Args:
            device_id: 设备ID

        Returns:
            True 如果设备已连接
        """
        driver = self._devices.get(device_id)
        return driver.is_connected if driver else False

    def count(self) -> int:
        """获取设备数量

        Returns:
            设备总数
        """
        return len(self._devices)

    def count_connected(self) -> int:
        """获取已连接设备数量

        Returns:
            已连接设备数量
        """
        return sum(1 for d in self._devices.values() if d.is_connected)

    # ========================================================================
    # 批量操作
    # ========================================================================

    async def connect_all(self) -> dict[str, bool]:
        """连接所有设备

        Returns:
            连接结果字典 {device_id: success}
        """
        results = {}
        for device_id in self._devices.keys():
            try:
                results[device_id] = await self.connect(device_id)
            except Exception as e:
                logger.error(
                    f"Failed to connect device {device_id}: {e}",
                    extra={"device_id": device_id},
                )
                results[device_id] = False
        return results

    async def call_all(self, method: str, **kwargs) -> dict[str, Any]:
        """在所有设备上调用同一方法

        Args:
            method: 方法名称
            **kwargs: 传递给方法的参数

        Returns:
            结果字典 {device_id: result}
        """
        results = {}
        for device_id in self._devices.keys():
            try:
                results[device_id] = await self.call(device_id, method, **kwargs)
            except Exception as e:
                logger.error(
                    f"Failed to call {method} on device {device_id}: {e}",
                    extra={"device_id": device_id, "method": method},
                )
                results[device_id] = {"error": str(e)}
        return results

    # ========================================================================
    # 上下文管理器支持
    # ========================================================================

    async def __aenter__(self) -> "DeviceController":
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        await self.disconnect_all()


# ============================================================================
# 全局控制器实例（延迟初始化）
# ============================================================================

_controller: Optional[DeviceController] = None


def get_controller() -> DeviceController:
    """获取全局控制器实例（延迟初始化）

    Returns:
        DeviceController 实例
    """
    global _controller
    if _controller is None:
        _controller = DeviceController()
    return _controller


def reset_controller() -> None:
    """重置全局控制器实例（用于测试）"""
    global _controller
    _controller = None


# 导出
__all__ = [
    "DeviceController",
    "get_controller",
    "reset_controller",
]
