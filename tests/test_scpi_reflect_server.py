"""SCPI 反射服务器测试（真实 TCP socket，离线可跑）。

覆盖：
- ``*IDN?`` 返回仪器标识
- ``set_voltage(5.0)`` 后 ``measure_voltage()`` 返回 5.0
- ``measure_current()`` 默认 0.1
- 不识别命令写入 ``-113`` 错误码，``*CLS`` 清空错误队列，且缓冲不乱序
- 多连接并发：各会话状态相互隔离
"""

from __future__ import annotations

import socket
import threading
from collections.abc import Iterator

import pytest

from tests.scpi_reflect_server import SCPIReflectServer

TIMEOUT = 5.0


class SCPIClient:
    """极简 SCPI over TCP 客户端（用于测试反射服务器）。"""

    def __init__(self, host: str, port: int) -> None:
        self._sock = socket.create_connection((host, port), timeout=TIMEOUT)
        self._reader = self._sock.makefile("rb")

    def write(self, command: str) -> None:
        """发送一条写命令（无响应）。"""
        self._sock.sendall((command + "\n").encode("utf-8"))

    def query(self, command: str) -> str:
        """发送一条查询命令并读取响应（去换行）。"""
        self._sock.sendall((command + "\n").encode("utf-8"))
        line = self._reader.readline()
        if not line:
            raise AssertionError(f"no response for {command!r}")
        return line.decode("utf-8").strip()

    def close(self) -> None:
        """关闭连接。"""
        try:
            self._reader.close()
        finally:
            self._sock.close()

    def __enter__(self) -> "SCPIClient":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()


@pytest.fixture
def server() -> Iterator[SCPIReflectServer]:
    """在临时端口启动反射服务器，用例结束后干净关闭。"""
    srv = SCPIReflectServer(host="127.0.0.1", port=0).start()
    try:
        yield srv
    finally:
        srv.stop()


@pytest.fixture
def client(server: SCPIReflectServer) -> Iterator[SCPIClient]:
    """连接到反射服务器的客户端。"""
    cli = SCPIClient(server.host, server.port)
    try:
        yield cli
    finally:
        cli.close()


def test_idn_query_returns_identity(client: SCPIClient) -> None:
    """``*IDN?`` 返回含制造商/型号字段的仪器标识。"""
    identity = client.query("*IDN?")

    parts = identity.split(",")
    assert len(parts) >= 2
    assert parts[0] == "MAT"
    assert parts[1] == "SCPI-Reflect"


def test_set_voltage_then_measure_voltage(client: SCPIClient) -> None:
    """设置电压 5.0 后测量返回最后设定值 5.0。"""
    client.write("SOURce1:VOLTage 5.0")

    assert float(client.query("MEASure1:VOLTage?")) == pytest.approx(5.0)


def test_measure_voltage_before_set_is_zero(client: SCPIClient) -> None:
    """未设定时测量电压为默认 0.0。"""
    assert float(client.query("MEASure1:VOLTage?")) == pytest.approx(0.0)


def test_measure_current_default_is_point_one(client: SCPIClient) -> None:
    """未设定时测量电流为默认 0.1A。"""
    assert float(client.query("MEASure1:CURRent?")) == pytest.approx(0.1)


def test_unknown_command_records_error_and_cls_clears(client: SCPIClient) -> None:
    """不识别命令写入 -113 错误码；``*CLS`` 清空错误队列。"""
    # 不识别查询：立即返回错误文本
    assert client.query("FROBNicate:WIDGET?") == '-113,"Undefined header"'

    # 错误进入队列，可经 SYST:ERR? 取回一次
    first = client.query("SYSTem:ERRor?")
    assert first.startswith("-113")
    assert "Undefined header" in first

    # 队列已空
    assert client.query("SYSTem:ERRor?").startswith("+0")

    # 再写一条错误后 *CLS 清空
    client.write("FROBNicate:WIDGET 1")
    client.write("*CLS")
    assert client.query("SYSTem:ERRor?").startswith("+0")


def test_unknown_command_does_not_desync_buffer(client: SCPIClient) -> None:
    """不识别命令后，后续命令仍按行正确解析（缓冲未被打乱）。"""
    client.write("BOGUS:COMMAND 1")
    client.write("SOURce1:VOLTage 3.3")

    assert float(client.query("MEASure1:VOLTage?")) == pytest.approx(3.3)


def test_multiple_connections_isolated_state(server: SCPIReflectServer) -> None:
    """多连接并发：各会话设定值相互隔离。"""
    client_a = SCPIClient(server.host, server.port)
    client_b = SCPIClient(server.host, server.port)
    try:
        client_a.write("SOURce1:VOLTage 7.5")
        client_b.write("SOURce1:VOLTage 2.0")

        assert float(client_a.query("MEASure1:VOLTage?")) == pytest.approx(7.5)
        assert float(client_b.query("MEASure1:VOLTage?")) == pytest.approx(2.0)
    finally:
        client_a.close()
        client_b.close()

    assert server.connections_served >= 2


def test_concurrent_queries_are_thread_safe(server: SCPIReflectServer) -> None:
    """并发线程各自连接查询，结果不串扰。"""
    results: dict[int, float] = {}
    errors: list[BaseException] = []

    def worker(index: int) -> None:
        try:
            with SCPIClient(server.host, server.port) as cli:
                target = float(index) + 0.5
                cli.write(f"SOURce1:VOLTage {target:.1f}")
                results[index] = float(cli.query("MEASure1:VOLTage?"))
        except BaseException as exc:  # noqa: BLE001 - 汇总到主线程断言
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=TIMEOUT)

    assert not errors, errors
    assert results == {i: i + 0.5 for i in range(5)}


def test_rst_resets_voltage(client: SCPIClient) -> None:
    """``*RST`` 复位设定电压到默认 0.0。"""
    client.write("SOURce1:VOLTage 9.9")
    client.write("*RST")

    assert float(client.query("MEASure1:VOLTage?")) == pytest.approx(0.0)


def test_log_file_records_command_and_response(server: SCPIReflectServer, tmp_path) -> None:
    """配置日志文件时，命令/响应逐条落盘（JSON Lines）。"""
    import json

    log_path = tmp_path / "scpi.log"
    logging_server = SCPIReflectServer(host="127.0.0.1", port=0, log_path=log_path).start()
    try:
        with SCPIClient(logging_server.host, logging_server.port) as cli:
            cli.query("*IDN?")
            cli.write("SOURce1:VOLTage 4.2")
    finally:
        logging_server.stop()

    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    commands = [r["command"] for r in records]
    assert "*IDN?" in commands
    assert "SOURce1:VOLTage 4.2" in commands
    idn_record = next(r for r in records if r["command"] == "*IDN?")
    assert idn_record["response"] == "MAT,SCPI-Reflect,SN0001,1.0"
