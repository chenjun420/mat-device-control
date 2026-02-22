"""设备驱动注册表

提供驱动发现和注册功能：
- DriverRegistry: 驱动注册表单例
- register_driver: 驱动注册装饰器
"""

from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Type

from modules.core.logging import get_logger
from modules.device.base import BaseDriver
from modules.device.enums import DeviceCategory

logger = get_logger(__name__)


@dataclass
class DriverInfo:
    """驱动信息数据类

    存储已注册驱动的元数据。

    Attributes:
        driver_class: 驱动类
        category: 设备类别
        manufacturer: 制造商
        model: 设备型号
    """

    driver_class: Type[BaseDriver]
    category: DeviceCategory
    manufacturer: str
    model: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典

        Returns:
            包含驱动信息的字典
        """
        return {
            "driver_class": self.driver_class,
            "category": self.category,
            "manufacturer": self.manufacturer,
            "model": self.model,
        }


class DriverRegistry:
    """设备驱动注册表

    单例模式实现的驱动注册表，提供：
    - 驱动注册和注销
    - 按类别/制造商/型号查询驱动
    - 驱动发现功能

    Usage:
        registry = DriverRegistry()
        registry.register_driver(
            driver_class=MyDriver,
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )
    """

    _instance: "DriverRegistry | None" = None
    _lock: Lock = Lock()

    def __new__(cls) -> "DriverRegistry":
        """创建单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._drivers: dict[str, DriverInfo] = {}
                    cls._instance._initialized = True
        return cls._instance

    @classmethod
    def get_instance(cls) -> "DriverRegistry":
        """获取单例实例

        Returns:
            DriverRegistry 单例实例
        """
        return cls()

    @classmethod
    def _clear_instance(cls) -> None:
        """清除单例实例（仅用于测试）"""
        with cls._lock:
            cls._instance = None

    def _make_key(
        self,
        category: DeviceCategory,
        manufacturer: str,
        model: str,
    ) -> str:
        """生成驱动注册键

        Args:
            category: 设备类别
            manufacturer: 制造商
            model: 设备型号

        Returns:
            唯一的驱动键
        """
        return f"{category.value}:{manufacturer}:{model}".lower()

    def register_driver(
        self,
        driver_class: Type[BaseDriver],
        category: DeviceCategory,
        manufacturer: str,
        model: str,
    ) -> None:
        """注册驱动

        Args:
            driver_class: 驱动类（必须继承 BaseDriver）
            category: 设备类别
            manufacturer: 制造商
            model: 设备型号

        Raises:
            TypeError: 驱动类无效
        """
        if driver_class is None or not (
            isinstance(driver_class, type) and issubclass(driver_class, BaseDriver)
        ):
            raise TypeError(
                f"driver_class must be a subclass of BaseDriver, got {driver_class}"
            )

        key = self._make_key(category, manufacturer, model)
        driver_info = DriverInfo(
            driver_class=driver_class,
            category=category,
            manufacturer=manufacturer,
            model=model,
        )

        self._drivers[key] = driver_info
        logger.debug(
            "Driver registered",
            extra={
                "key": key,
                "driver": driver_class.__name__,
                "category": category.value,
                "manufacturer": manufacturer,
                "model": model,
            },
        )

    def unregister_driver(
        self,
        category: DeviceCategory,
        manufacturer: str,
        model: str,
    ) -> bool:
        """注销驱动

        Args:
            category: 设备类别
            manufacturer: 制造商
            model: 设备型号

        Returns:
            是否成功注销
        """
        key = self._make_key(category, manufacturer, model)
        if key in self._drivers:
            del self._drivers[key]
            logger.debug("Driver unregistered", extra={"key": key})
            return True
        return False

    def get_driver(
        self,
        category: DeviceCategory,
        manufacturer: str,
        model: str,
    ) -> Type[BaseDriver] | None:
        """获取驱动类

        Args:
            category: 设备类别
            manufacturer: 制造商
            model: 设备型号

        Returns:
            驱动类，如果未找到返回 None
        """
        key = self._make_key(category, manufacturer, model)
        driver_info = self._drivers.get(key)
        return driver_info.driver_class if driver_info else None

    def get_driver_info(
        self,
        category: DeviceCategory,
        manufacturer: str,
        model: str,
    ) -> dict[str, Any] | None:
        """获取驱动信息

        Args:
            category: 设备类别
            manufacturer: 制造商
            model: 设备型号

        Returns:
            驱动信息字典，如果未找到返回 None
        """
        key = self._make_key(category, manufacturer, model)
        driver_info = self._drivers.get(key)
        return driver_info.to_dict() if driver_info else None

    def get_drivers_by_category(
        self, category: DeviceCategory
    ) -> list[Type[BaseDriver]]:
        """按类别获取驱动

        Args:
            category: 设备类别

        Returns:
            该类别下的所有驱动类列表
        """
        return [
            info.driver_class
            for info in self._drivers.values()
            if info.category == category
        ]

    def get_drivers_by_manufacturer(self, manufacturer: str) -> list[Type[BaseDriver]]:
        """按制造商获取驱动

        Args:
            manufacturer: 制造商名称

        Returns:
            该制造商的所有驱动类列表
        """
        manufacturer_lower = manufacturer.lower()
        return [
            info.driver_class
            for info in self._drivers.values()
            if info.manufacturer.lower() == manufacturer_lower
        ]

    def get_all_drivers(self) -> list[Type[BaseDriver]]:
        """获取所有已注册驱动

        Returns:
            所有驱动类列表
        """
        return [info.driver_class for info in self._drivers.values()]

    def is_registered(
        self,
        category: DeviceCategory,
        manufacturer: str,
        model: str,
    ) -> bool:
        """检查驱动是否已注册

        Args:
            category: 设备类别
            manufacturer: 制造商
            model: 设备型号

        Returns:
            驱动是否已注册
        """
        key = self._make_key(category, manufacturer, model)
        return key in self._drivers

    def count(self) -> int:
        """获取已注册驱动数量

        Returns:
            驱动数量
        """
        return len(self._drivers)

    def clear(self) -> None:
        """清除所有已注册驱动"""
        self._drivers.clear()
        logger.debug("All drivers cleared")


def register_driver(
    category: DeviceCategory,
    manufacturer: str,
    model: str,
) -> Callable[[Type[BaseDriver]], Type[BaseDriver]]:
    """驱动注册装饰器

    用于便捷地将驱动类注册到注册表。

    Args:
        category: 设备类别
        manufacturer: 制造商
        model: 设备型号

    Returns:
        装饰器函数

    Example:
        @register_driver(
            category=DeviceCategory.POWER_SUPPLY,
            manufacturer="Keysight",
            model="E36312A",
        )
        class KeysightE36312ADriver(BaseDriver):
            ...
    """

    def decorator(cls: Type[BaseDriver]) -> Type[BaseDriver]:
        registry = DriverRegistry()
        registry.register_driver(
            driver_class=cls,
            category=category,
            manufacturer=manufacturer,
            model=model,
        )
        return cls

    return decorator


# 导出
__all__ = [
    "DriverInfo",
    "DriverRegistry",
    "register_driver",
]
