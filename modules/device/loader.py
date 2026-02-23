"""设备初始化加载器

在应用启动时根据配置文件自动加载设备驱动。
"""

import asyncio
from pathlib import Path
from typing import Any

import tomllib

from modules.core.logging import get_logger
from modules.device.controller import get_controller, reset_controller
from modules.device.enums import DeviceCategory, ConnectionType, ProtocolType

logger = get_logger(__name__)


class DeviceLoader:
    """设备加载器

    负责从配置文件加载设备配置并在启动时初始化设备。
    """

    def __init__(self, config_file: str = "devices.toml"):
        """初始化设备加载器

        Args:
            config_file: 设备配置文件路径
        """
        self.config_file = Path(config_file)
        self._device_configs: list[dict[str, Any]] = []

    def load_config(self) -> list[dict[str, Any]]:
        """从配置文件加载设备配置

        Returns:
            设备配置列表
        """
        if not self.config_file.exists():
            logger.warning(
                f"Device config file not found: {self.config_file}",
                extra={"config_file": str(self.config_file)},
            )
            return []

        try:
            with open(self.config_file, "rb") as f:
                data = tomllib.load(f)

            devices = data.get("devices", [])
            logger.info(
                f"Loaded {len(devices)} device configurations",
                extra={
                    "config_file": str(self.config_file),
                    "device_count": len(devices),
                },
            )
            return devices
        except Exception as e:
            logger.error(
                f"Failed to load device config: {e}",
                extra={"config_file": str(self.config_file), "error": str(e)},
            )
            return []

    async def initialize_devices(
        self, auto_connect: bool = True, only_enabled: bool = True
    ) -> dict[str, dict[str, Any]]:
        """初始化所有设备

        Args:
            auto_connect: 是否自动连接标记为 auto_connect 的设备
            only_enabled: 是否只初始化启用的设备

        Returns:
            初始化结果字典 {device_id: {"success": bool, "connected": bool, "error": str|None}}
        """
        configs = self.load_config()
        results = {}

        if not configs:
            logger.info("No devices to initialize")
            return results

        controller = get_controller()

        for device_config in configs:
            device_id = device_config.get("device_id", "unknown")

            # 检查是否启用
            if only_enabled and not device_config.get("enabled", True):
                logger.info(
                    f"Skipping disabled device: {device_id}",
                    extra={"device_id": device_id},
                )
                results[device_id] = {
                    "success": False,
                    "connected": False,
                    "error": "Device is disabled",
                }
                continue

            try:
                # 创建设备
                await controller.create(device_id, device_config)
                results[device_id] = {
                    "success": True,
                    "connected": False,
                    "error": None,
                }

                logger.info(
                    f"Device created: {device_id}",
                    extra={
                        "device_id": device_id,
                        "model": device_config.get("model"),
                        "manufacturer": device_config.get("manufacturer"),
                    },
                )

                # 自动连接（如果配置要求）
                should_connect = auto_connect and device_config.get(
                    "auto_connect", True
                )
                if should_connect:
                    try:
                        connected = await controller.connect(device_id)
                        results[device_id]["connected"] = connected

                        if connected:
                            logger.info(
                                f"Device connected: {device_id}",
                                extra={"device_id": device_id},
                            )
                        else:
                            logger.warning(
                                f"Device connection failed: {device_id}",
                                extra={"device_id": device_id},
                            )
                    except Exception as e:
                        results[device_id]["connected"] = False
                        results[device_id]["error"] = str(e)
                        logger.error(
                            f"Failed to connect device {device_id}: {e}",
                            extra={"device_id": device_id, "error": str(e)},
                        )

            except Exception as e:
                results[device_id] = {
                    "success": False,
                    "connected": False,
                    "error": str(e),
                }
                logger.error(
                    f"Failed to create device {device_id}: {e}",
                    extra={"device_id": device_id, "error": str(e)},
                )

        # 统计结果
        success_count = sum(1 for r in results.values() if r["success"])
        connected_count = sum(1 for r in results.values() if r["connected"])

        logger.info(
            f"Device initialization complete: {success_count}/{len(configs)} created, {connected_count} connected",
            extra={
                "total": len(configs),
                "created": success_count,
                "connected": connected_count,
            },
        )

        return results

    async def shutdown_devices(self) -> None:
        """关闭所有设备"""
        controller = get_controller()
        await controller.disconnect_all()
        logger.info("All devices disconnected")


# 全局加载器实例
_loader: DeviceLoader | None = None


def get_device_loader(config_file: str = "devices.toml") -> DeviceLoader:
    """获取设备加载器实例

    Args:
        config_file: 设备配置文件路径

    Returns:
        DeviceLoader 实例
    """
    global _loader
    if _loader is None:
        _loader = DeviceLoader(config_file)
    return _loader


def reset_device_loader() -> None:
    """重置设备加载器（用于测试）"""
    global _loader
    _loader = None
    reset_controller()


# 导出
__all__ = [
    "DeviceLoader",
    "get_device_loader",
    "reset_device_loader",
]
