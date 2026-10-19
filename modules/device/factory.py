"""设备驱动工厂

提供设备驱动的注册、创建和管理功能。
采用懒加载和缓存机制优化内存占用。
"""

import importlib
import sys
from typing import Dict, List, Optional, Type

from modules.device.base import BaseDriver, DeviceConfig


class DriverFactory:
    """设备驱动工厂

    管理设备驱动的注册和创建。
    采用懒加载模式，仅在需要时加载驱动类。

    Attributes:
        _driver_paths: 驱动路径注册表 {key: module_path}
        _driver_classes: 已加载的驱动类缓存 {key: driver_class}
        _loaded_modules: 已加载的模块集合
    """

    def __init__(self):
        """初始化驱动工厂"""
        self._driver_paths: Dict[str, str] = {}
        self._driver_classes: Dict[str, Type[BaseDriver]] = {}
        self._loaded_modules: set[str] = set()
        self._register_default_drivers()

    def _register_default_drivers(self) -> None:
        """注册默认驱动路径（不加载驱动类）"""
        # 电源设备
        self._driver_paths["Keysight.E36312A"] = (
            "modules.device.drivers.keysight.e36312a:KeysightE36312A"
        )

        # 示波器设备
        self._driver_paths["Siglent.SDS1000X-E"] = (
            "modules.device.drivers.siglent.sds1000x:SiglentSDS1000X"
        )
        self._driver_paths["Siglent.SDS1104X-E"] = (
            "modules.device.drivers.siglent.sds1000x:SiglentSDS1000X"
        )

        # 通用 SCPI 电源（对齐 ATEStudio edge 通用设备契约：
        # set_voltage(value, channel?) / measure_voltage(channel?)）
        self._driver_paths["MAT.GenericPSU"] = (
            "modules.device.drivers.generic.scpi_psu:GenericSCPIPowerSupply"
        )

        # 虚拟仪器（确定性行为模型，无硬件时跑通 ATEStudio PA601 commissioning）
        self._driver_paths["MAT.VirtualPSU"] = (
            "modules.device.drivers.virtual:VirtualPSU"
        )
        self._driver_paths["MAT.VirtualDMM"] = (
            "modules.device.drivers.virtual:VirtualDMM"
        )
        self._driver_paths["MAT.VirtualELoad"] = (
            "modules.device.drivers.virtual:VirtualELoad"
        )
        self._driver_paths["MAT.VirtualScope"] = (
            "modules.device.drivers.virtual:VirtualScope"
        )
        self._driver_paths["MAT.VirtualACSource"] = (
            "modules.device.drivers.virtual:VirtualACSource"
        )
        self._driver_paths["MAT.VirtualPowerMeter"] = (
            "modules.device.drivers.virtual:VirtualPowerMeter"
        )
        self._driver_paths["MAT.VirtualSafety"] = (
            "modules.device.drivers.virtual:VirtualSafety"
        )
        self._driver_paths["MAT.VirtualThermo"] = (
            "modules.device.drivers.virtual:VirtualThermo"
        )
        self._driver_paths["MAT.VirtualAging"] = (
            "modules.device.drivers.virtual:VirtualAging"
        )

    def create_driver(self, config: DeviceConfig) -> BaseDriver:
        """创建设备驱动

        使用缓存机制，避免重复加载驱动类。

        Args:
            config: 设备配置

        Returns:
            设备驱动实例

        Raises:
            ValueError: 不支持的设备型号
            ImportError: 驱动模块加载失败
        """
        driver_key = f"{config.manufacturer}.{config.model}"

        if driver_key not in self._driver_paths:
            raise ValueError(f"Unsupported device: {driver_key}")

        # 从缓存获取驱动类
        driver_class = self._driver_classes.get(driver_key)

        if driver_class is None:
            # 首次加载驱动类
            driver_class = self._load_driver_class(driver_key)
            self._driver_classes[driver_key] = driver_class

        return driver_class(config)

    def _load_driver_class(self, driver_key: str) -> Type[BaseDriver]:
        """加载驱动类

        Args:
            driver_key: 驱动键 (manufacturer.model)

        Returns:
            驱动类

        Raises:
            ImportError: 模块加载失败
        """
        driver_path = self._driver_paths[driver_key]

        # 支持两种格式:
        # 1. "module.path:ClassName" (推荐)
        # 2. "module.path.ClassName" (兼容旧格式)
        if ":" in driver_path:
            module_path, class_name = driver_path.split(":", 1)
        else:
            module_path, class_name = driver_path.rsplit(".", 1)

        # 检查模块是否已加载
        if module_path not in self._loaded_modules:
            try:
                # 动态导入模块
                module = importlib.import_module(module_path)
                self._loaded_modules.add(module_path)
            except ImportError as e:
                raise ImportError(
                    f"Failed to load driver module '{module_path}': {e}"
                ) from e
        else:
            # 从 sys.modules 获取已加载的模块
            module = sys.modules[module_path]

        # 获取驱动类
        driver_class = getattr(module, class_name, None)
        if driver_class is None:
            raise ImportError(
                f"Driver class '{class_name}' not found in module '{module_path}'"
            )

        return driver_class

    def register_driver(self, manufacturer: str, model: str, driver_path: str) -> None:
        """注册驱动路径

        Args:
            manufacturer: 制造商
            model: 型号
            driver_path: 驱动路径
                格式: "module.path:ClassName" 或 "module.path.ClassName"
        """
        driver_key = f"{manufacturer}.{model}"
        self._driver_paths[driver_key] = driver_path

        # 如果该驱动已加载，清除缓存
        if driver_key in self._driver_classes:
            del self._driver_classes[driver_key]

    def unregister_driver(self, manufacturer: str, model: str) -> bool:
        """注销驱动

        Args:
            manufacturer: 制造商
            model: 型号

        Returns:
            True 如果成功注销，False 如果驱动不存在
        """
        driver_key = f"{manufacturer}.{model}"

        if driver_key in self._driver_paths:
            del self._driver_paths[driver_key]
            # 清除缓存
            self._driver_classes.pop(driver_key, None)
            return True
        return False

    def is_device_supported(self, config: DeviceConfig) -> bool:
        """检查设备是否支持

        Args:
            config: 设备配置

        Returns:
            True如果支持，False否则
        """
        driver_key = f"{config.manufacturer}.{config.model}"
        return driver_key in self._driver_paths

    def get_supported_devices(self) -> List[str]:
        """获取支持的设备列表

        Returns:
            支持的设备列表，格式: ["manufacturer.model", ...]
        """
        return list(self._driver_paths.keys())

    def get_loaded_drivers(self) -> List[str]:
        """获取已加载的驱动列表

        Returns:
            已加载驱动的键列表
        """
        return list(self._driver_classes.keys())

    def get_loaded_modules(self) -> List[str]:
        """获取已加载的模块列表

        Returns:
            已加载模块的路径列表
        """
        return list(self._loaded_modules)

    def clear_cache(self) -> None:
        """清除驱动类缓存

        清除所有已加载的驱动类缓存，但不卸载模块。
        """
        self._driver_classes.clear()

    def preload_drivers(self, driver_keys: Optional[List[str]] = None) -> None:
        """预加载驱动类

        可选地预加载指定的驱动类到内存中。

        Args:
            driver_keys: 要预加载的驱动键列表，None 表示预加载所有
        """
        keys_to_load = driver_keys or list(self._driver_paths.keys())

        for key in keys_to_load:
            if key in self._driver_paths and key not in self._driver_classes:
                try:
                    self._load_driver_class(key)
                except ImportError:
                    # 预加载失败不抛出异常，仅记录
                    pass

    def get_memory_usage(self) -> Dict[str, int]:
        """获取内存使用统计

        Returns:
            包含统计信息的字典
        """
        return {
            "registered_drivers": len(self._driver_paths),
            "loaded_drivers": len(self._driver_classes),
            "loaded_modules": len(self._loaded_modules),
        }


# ============================================================================
# 延迟初始化的全局工厂实例
# ============================================================================

_factory: Optional[DriverFactory] = None


def get_factory() -> DriverFactory:
    """获取全局工厂实例（延迟初始化）

    Returns:
        驱动工厂实例
    """
    global _factory
    if _factory is None:
        _factory = DriverFactory()
    return _factory


def reset_factory() -> None:
    """重置全局工厂实例

    主要用于测试环境。
    """
    global _factory
    _factory = None


# 导出
__all__ = ["DriverFactory", "get_factory", "reset_factory"]
