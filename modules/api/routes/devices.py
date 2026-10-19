"""设备操作路由 - 反射式设备方法调用

提供 `POST /devices/{device_id}/call` 端点，供 ATEStudio edge 的
`MatDeviceHttpDriver` 通过 HTTP 调用 mat-device-control 中的设备方法。

端点在 method 白名单约束下，反射调用 `DeviceController.call()`：

- 白名单 = 硬编码基础集 ∪ `devices.toml` 中的 `allowed_methods` ∪ 环境变量追加项
- 任何 `_` 开头的方法名（如 `__init__`）一律拒绝，防止反射攻击
- device_id 不存在返回 404；方法执行异常返回 500

安全说明（决策 D13 / 风险 R16 延后）：
    当前仅内网暴露 + method 白名单兜底，**本阶段不引入鉴权**。
    生产化时应在统一入口补充 `X-API-Key` 或 mTLS 校验；届时再评估 R16。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import tomllib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from modules.core.logging import get_logger
from modules.device.controller import get_controller

router = APIRouter(prefix="/devices", tags=["devices"])
logger = get_logger(__name__)


# 硬编码基础方法白名单（架构升级方案 §5 A.2）
METHOD_ALLOWLIST_BASE: frozenset[str] = frozenset(
    {
        "set_voltage",
        "set_current",
        "set_load",
        "set_frequency",
        "measure_voltage",
        "measure_current",
        "measure_frequency",
        "connect",
        "disconnect",
        "reset",
        "identify",
        "get_status",
        "read",
        "write",
        "query",
    }
)

# 环境变量：追加白名单方法（逗号分隔），供现场按需放行扩展方法
ENV_METHOD_ALLOWLIST = "MAT_DEVICE_METHOD_ALLOWLIST"
# 环境变量：设备配置文件路径（用于读取可选的 allowed_methods）
ENV_DEVICE_CONFIG_FILE = "MAT_DEVICE_CONFIG_FILE"
# 默认设备配置文件
DEFAULT_DEVICE_CONFIG_FILE = "devices.toml"


class DeviceCallRequest(BaseModel):
    """设备方法调用请求模型"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "method": "set_voltage",
                "kwargs": {"channel": 1, "voltage": 12.0},
            }
        }
    )

    method: str = Field(..., description="要调用的设备方法名（必须在白名单内）")
    kwargs: dict[str, Any] = Field(
        ..., description="传递给设备方法的关键字参数"
    )


class DeviceCallResponse(BaseModel):
    """设备方法调用响应模型"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"result": {"channel": 1, "voltage": 12.0}, "error": None}
        }
    )

    result: Any = Field(default=None, description="设备方法返回值")
    error: str | None = Field(default=None, description="错误信息，成功时为 None")


def _collect_methods(raw: Any) -> set[str]:
    """从原始值收集合法方法名。

    Args:
        raw: 期望为字符串列表；其他类型一律忽略

    Returns:
        收集到的方法名集合
    """
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw if isinstance(item, str) and item}


def _read_file_allowlist(config_file: str | Path | None = None) -> frozenset[str]:
    """从设备配置文件读取可选的 allowed_methods 白名单。

    支持两类位置：
    - 顶层 `[api] allowed_methods = [...]`
    - 每个 `[[devices]]` 条目内的 `allowed_methods = [...]`

    Args:
        config_file: 配置文件路径；None 时依次使用环境变量与默认值

    Returns:
        从文件收集到的方法名集合；文件缺失或解析失败时返回空集合（不影响基础白名单）
    """
    path_str = config_file or os.environ.get(
        ENV_DEVICE_CONFIG_FILE, DEFAULT_DEVICE_CONFIG_FILE
    )
    path = Path(path_str)
    if not path.exists():
        return frozenset()

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:  # noqa: BLE001 - 配置文件损坏不应阻断服务
        logger.warning(
            f"读取设备配置失败，忽略文件白名单: {e}",
            extra={"config_file": str(path)},
        )
        return frozenset()

    names: set[str] = set()
    api_section = data.get("api")
    if isinstance(api_section, dict):
        names.update(_collect_methods(api_section.get("allowed_methods")))
    for device in data.get("devices", []) or []:
        if isinstance(device, dict):
            names.update(_collect_methods(device.get("allowed_methods")))

    return frozenset(names)


def _read_env_allowlist() -> frozenset[str]:
    """读取环境变量中追加的方法白名单。

    Returns:
        环境变量 `MAT_DEVICE_METHOD_ALLOWLIST` 中解析出的方法名集合
    """
    raw = os.environ.get(ENV_METHOD_ALLOWLIST, "")
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def get_method_allowlist() -> frozenset[str]:
    """计算有效方法白名单。

    有效白名单 = 基础集 ∪ 配置文件 allowed_methods ∪ 环境变量追加项。
    环境变量仅用于**扩展**白名单；基础集始终生效，避免误删安全方法。

    Returns:
        允许调用的方法名集合
    """
    return METHOD_ALLOWLIST_BASE | _read_file_allowlist() | _read_env_allowlist()


def _validate_method(method: str, allowlist: frozenset[str]) -> None:
    """校验方法名是否合法且在白名单内。

    Args:
        method: 方法名
        allowlist: 有效白名单

    Raises:
        HTTPException: 400 - 方法名为空、以下划线开头（防反射），或不在白名单
    """
    if not method or method.startswith("_"):
        raise HTTPException(status_code=400, detail="非法方法名")
    if method not in allowlist:
        raise HTTPException(status_code=400, detail="method 不在白名单")


@router.post(
    "/{device_id}/call",
    response_model=DeviceCallResponse,
    summary="反射调用设备方法",
    description="""
在 method 白名单约束下，反射调用指定设备的方法。

**请求体：**
* `method` - 设备方法名，必须位于白名单内
* `kwargs` - 传递给设备方法的关键字参数

**白名单：** 硬编码基础集 + `devices.toml` 的 `allowed_methods` + 环境变量追加项。
任何 `_` 开头的方法名（如 `__init__`）都会被拒绝。

**安全：** 当前仅内网暴露 + method 白名单兜底，尚未引入鉴权（决策 D13 / R16 延后）。
""",
    responses={
        200: {"description": "调用成功"},
        400: {"description": "方法名非法或不在白名单"},
        404: {"description": "设备不存在"},
        500: {"description": "设备方法执行异常"},
    },
)
async def call_device_method(
    device_id: str, request: DeviceCallRequest
) -> DeviceCallResponse:
    """反射调用设备方法。

    Args:
        device_id: 设备唯一标识符
        request: 调用请求，包含方法名与关键字参数

    Returns:
        DeviceCallResponse: 包含方法返回值

    Raises:
        HTTPException: 400 方法非法/不在白名单；404 设备不存在；500 调用异常
    """
    allowlist = get_method_allowlist()
    _validate_method(request.method, allowlist)

    controller = get_controller()
    if not controller.exists(device_id):
        raise HTTPException(status_code=404, detail=f"设备 '{device_id}' 不存在")

    try:
        result = await controller.call(device_id, request.method, **request.kwargs)
    except Exception as e:  # noqa: BLE001 - 统一转换为 500 并记录原始异常
        logger.error(
            f"设备方法调用失败: {e}",
            extra={
                "device_id": device_id,
                "method": request.method,
                "error": str(e),
                "exc_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=500, detail=f"设备方法调用失败: {e}"
        ) from e

    logger.info(
        "Device method called",
        extra={"device_id": device_id, "method": request.method},
    )
    return DeviceCallResponse(result=result, error=None)
