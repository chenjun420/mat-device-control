"""Tests for Modbus protocol"""

import pytest
from unittest.mock import patch
from modules.device.protocols.modbus import ModbusProtocol


@pytest.mark.asyncio
async def test_modbus_protocol_creation():
    """测试Modbus协议处理器创建"""
    protocol = ModbusProtocol()
    assert protocol is not None
    assert protocol.is_connected is False


@pytest.mark.asyncio
async def test_modbus_connect_rtu():
    """测试Modbus RTU连接"""
    protocol = ModbusProtocol()

    # 测试RTU连接字符串解析
    with patch.object(protocol, "_connect_rtu", return_value=True) as mock_connect:
        result = await protocol.connect("MODBUS_RTU::COM1::9600::8N1")
        assert result is True
        mock_connect.assert_called_once()


@pytest.mark.asyncio
async def test_modbus_connect_tcp():
    """测试Modbus TCP连接"""
    protocol = ModbusProtocol()

    # 测试TCP连接字符串解析
    with patch.object(protocol, "_connect_tcp", return_value=True) as mock_connect:
        result = await protocol.connect("MODBUS_TCP::192.168.1.100::502")
        assert result is True
        mock_connect.assert_called_once()


@pytest.mark.asyncio
async def test_modbus_parse_rtu_resource():
    """测试RTU资源字符串解析"""
    protocol = ModbusProtocol()

    port, baudrate, config = protocol._parse_rtu_resource("MODBUS_RTU::COM1::9600::8N1")

    assert port == "COM1"
    assert baudrate == 9600
    assert config == {"bytesize": 8, "parity": "N", "stopbits": 1}


@pytest.mark.asyncio
async def test_modbus_parse_tcp_resource():
    """测试TCP资源字符串解析"""
    protocol = ModbusProtocol()

    host, port = protocol._parse_tcp_resource("MODBUS_TCP::192.168.1.100::502")

    assert host == "192.168.1.100"
    assert port == 502


@pytest.mark.asyncio
async def test_modbus_parse_tcp_resource_default_port():
    """测试TCP资源字符串解析（默认端口）"""
    protocol = ModbusProtocol()

    host, port = protocol._parse_tcp_resource("MODBUS_TCP::192.168.1.100")

    assert host == "192.168.1.100"
    assert port == 502  # 默认端口


@pytest.mark.asyncio
async def test_modbus_parse_serial_config():
    """测试串口配置解析"""
    protocol = ModbusProtocol()

    # 8N1格式
    config = protocol._parse_serial_config("8N1")
    assert config == {"bytesize": 8, "parity": "N", "stopbits": 1}

    # 8E1格式
    config = protocol._parse_serial_config("8E1")
    assert config == {"bytesize": 8, "parity": "E", "stopbits": 1}

    # 7O2格式
    config = protocol._parse_serial_config("7O2")
    assert config == {"bytesize": 7, "parity": "O", "stopbits": 2}


@pytest.mark.asyncio
async def test_modbus_unsupported_resource():
    """测试不支持的资源类型"""
    protocol = ModbusProtocol()

    # 不支持的资源类型应该返回False
    result = await protocol.connect("UNKNOWN::resource")
    assert result is False


@pytest.mark.asyncio
async def test_modbus_disconnect():
    """测试断开连接"""
    protocol = ModbusProtocol()

    # Mock连接
    protocol._connection = True  # 简单mock

    await protocol.disconnect()

    assert protocol._connection is None
