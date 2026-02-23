"""Tests for base protocol"""

import pytest
from abc import ABC


def test_base_protocol_is_abstract():
    """测试BaseProtocol是抽象类"""
    from modules.device.protocols.base_protocol import BaseProtocol

    # 验证BaseProtocol是抽象类
    assert issubclass(BaseProtocol, ABC)


def test_base_protocol_has_required_methods():
    """测试BaseProtocol定义了必需的方法"""
    from modules.device.protocols.base_protocol import BaseProtocol

    # 验证抽象方法存在
    assert hasattr(BaseProtocol, "connect")
    assert hasattr(BaseProtocol, "disconnect")
    assert hasattr(BaseProtocol, "write")
    assert hasattr(BaseProtocol, "read")
    assert hasattr(BaseProtocol, "query")
    assert hasattr(BaseProtocol, "is_connected")


def test_base_protocol_has_required_methods_are_abstract():
    """测试BaseProtocol的必需方法是抽象方法"""
    from modules.device.protocols.base_protocol import BaseProtocol
    import inspect

    # 验证抽象方法是抽象的
    assert getattr(BaseProtocol.connect, "__isabstractmethod__", False) is True
    assert getattr(BaseProtocol.disconnect, "__isabstractmethod__", False) is True
    assert getattr(BaseProtocol.write, "__isabstractmethod__", False) is True
    assert getattr(BaseProtocol.read, "__isabstractmethod__", False) is True
    assert getattr(BaseProtocol.query, "__isabstractmethod__", False) is True
    assert getattr(BaseProtocol.is_connected, "__isabstractmethod__", False) is True
