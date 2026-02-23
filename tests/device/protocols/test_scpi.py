"""Tests for SCPI protocol"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from modules.device.protocols.scpi import SCPIProtocol


@pytest.mark.asyncio
async def test_scpi_protocol_creation():
    """测试SCPI协议处理器创建"""
    protocol = SCPIProtocol()
    assert protocol is not None
    assert protocol.is_connected is False


@pytest.mark.asyncio
async def test_scpi_connect_tcpip():
    """测试SCPI TCP/IP连接"""
    protocol = SCPIProtocol()

    # Mock连接方法
    with patch.object(protocol, "_connect_tcpip", return_value=True) as mock_connect:
        result = await protocol.connect("TCPIP0::192.168.1.100::5025::SOCKET")

        assert result is True
        mock_connect.assert_called_once_with("TCPIP0::192.168.1.100::5025::SOCKET")


@pytest.mark.asyncio
async def test_scpi_connect_usb():
    """测试SCPI USB连接"""
    protocol = SCPIProtocol()

    with patch.object(protocol, "_connect_usb", return_value=True) as mock_connect:
        result = await protocol.connect("USB0::0x1234::0x5678::INSTR")

        assert result is True
        mock_connect.assert_called_once_with("USB0::0x1234::0x5678::INSTR")


@pytest.mark.asyncio
async def test_scpi_connect_gpib():
    """测试SCPI GPIB连接"""
    protocol = SCPIProtocol()

    with patch.object(protocol, "_connect_gpib", return_value=True) as mock_connect:
        result = await protocol.connect("GPIB0::1::INSTR")

        assert result is True
        mock_connect.assert_called_once_with("GPIB0::1::INSTR")


@pytest.mark.asyncio
async def test_scpi_query_format():
    """测试SCPI查询格式"""
    protocol = SCPIProtocol()

    # Mock内部方法
    with (
        patch.object(protocol, "write") as mock_write,
        patch.object(protocol, "read", return_value="+1.234E+00") as mock_read,
    ):
        result = await protocol.query("*IDN?")

        mock_write.assert_called_once_with("*IDN?")
        mock_read.assert_called_once()
        assert result == "+1.234E+00"


@pytest.mark.asyncio
async def test_scpi_write_not_connected():
    """测试未连接时写入命令抛出异常"""
    protocol = SCPIProtocol()

    with pytest.raises(RuntimeError, match="Not connected"):
        await protocol.write("*IDN?")


@pytest.mark.asyncio
async def test_scpi_read_not_connected():
    """测试未连接时读取数据抛出异常"""
    protocol = SCPIProtocol()

    with pytest.raises(RuntimeError, match="Not connected"):
        await protocol.read()


@pytest.mark.asyncio
async def test_scpi_disconnect():
    """测试断开连接"""
    protocol = SCPIProtocol()

    # Mock连接
    mock_conn = MagicMock()
    mock_conn.disconnect = AsyncMock()
    protocol._connection = mock_conn

    await protocol.disconnect()

    assert protocol._connection is None
    mock_conn.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_scpi_parse_tcpip_resource():
    """测试TCP/IP资源字符串解析"""
    protocol = SCPIProtocol()

    # 测试标准格式
    host, port = protocol._parse_tcpip_resource("TCPIP0::192.168.1.100::5025::SOCKET")
    assert host == "192.168.1.100"
    assert port == 5025

    # 测试无端口格式（默认5025）
    host, port = protocol._parse_tcpip_resource("TCPIP0::192.168.1.100::INSTR")
    assert host == "192.168.1.100"
    assert port == 5025


@pytest.mark.asyncio
async def test_scpi_unsupported_resource():
    """测试不支持的资源类型"""
    protocol = SCPIProtocol()

    # 不支持的资源类型应该返回False
    result = await protocol.connect("UNKNOWN::resource")
    assert result is False
