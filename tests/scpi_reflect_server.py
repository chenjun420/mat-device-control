"""SCPI 反射服务器 —— 物理仪器的最小可用替代（Phase A.4 真机替代）。

用途
----
整机端到端 demo 需要一条**真实**的 SCPI over TCP 链路：

    ATEStudio edge → HTTP → mat-device-control → SCPI(TCP) → 仪器

物理仪器未接入（决策 D2）。本模块以纯标准库实现一个 SCPI 反射服务器，
在 TCPIP 端口上伪装成一台可编程电源（PSU），使 SCPI 层走真实 socket 而非
进程内桩。它是"最近真机的替代"，不是内部仿真。

对应资源串::

    TCPIP0:0.0.0.0:{port}::SOCKET

（VISA 资源串仅描述端点；服务端只需在该 TCP 端口监听，SCPI 报文按行分帧，
命令以 ``\\n`` 结尾，响应同样以 ``\\n`` 结尾。）

支持的 SCPI 子集
----------------
* ``*IDN?``                  → 仪器标识（默认 ``MAT,SCPI-Reflect,SN0001,1.0``）
* ``*RST`` / ``*CLS``        → 复位设定值 / 清空错误队列
* ``*OPC?``                  → ``1``
* ``SYSTem:ERRor?``          → 错误队列首条（``+0,"No error"`` 或 ``-113,...``）
* ``[SOURce]n:VOLTage <v>``  → 记录设定电压（``MEASure:VOLTage?`` 返回最后设定值）
* ``[SOURce]n:CURRent <v>``  → 记录设定电流
* ``MEASure[n]:VOLTage?``    → 返回最后设定电压
* ``MEASure[n]:CURRent?``    → 返回设定电流（默认 0.1A）
* 无法识别 → 记录 ``-113,"Undefined header"``；若为查询则立即返回该错误文本。

分帧与容错
----------
每个 TCP 连接是一条独立会话（各自的设定值 / 错误队列），因此一个进程可同时
服务多个"仪器实例"（如 psu001 / psu002）。读缓冲按 ``\\n`` 切分，未识别命令
不会打乱后续命令的边界。

CLI::

    python tests/scpi_reflect_server.py --port 5025
    SCPI_REFLECT_PORT=5025 SCPI_REFLECT_LOG=scpi.log python tests/scpi_reflect_server.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5025
DEFAULT_IDENTITY = "MAT,SCPI-Reflect,SN0001,1.0"
DEFAULT_CURRENT = 0.1

#: 环境变量：监听端口 / 监听地址 / 仪器标识 / 报文日志文件
ENV_PORT = "SCPI_REFLECT_PORT"
ENV_HOST = "SCPI_REFLECT_HOST"
ENV_IDENTITY = "SCPI_REFLECT_IDN"
ENV_LOG = "SCPI_REFLECT_LOG"

#: SCPI 数值语法（可带符号、小数、科学计数）
_NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

#: 命令 → 匹配（大小写不敏感，可选通道号）。顺序即匹配优先级。
_RE_SET_VOLTAGE = re.compile(rf"^SOUR(?:CE)?\d*:VOLT(?:AGE)?\s+({_NUMBER})$")
_RE_SET_CURRENT = re.compile(rf"^SOUR(?:CE)?\d*:CURR(?:ENT)?\s+({_NUMBER})$")
_RE_MEAS_VOLTAGE = re.compile(r"^MEAS(?:URE)?\d*:VOLT(?:AGE)?\?$")
_RE_MEAS_CURRENT = re.compile(r"^MEAS(?:URE)?\d*:CURR(?:ENT)?\?$")


@dataclass
class ReflectSession:
    """单条 SCPI 会话的仪器状态。

    Attributes:
        voltage: 最后一次 ``[SOURce]:VOLTage`` 设定值（伏）。
        current: 最后一次 ``[SOURce]:CURRent`` 设定值（安）。
        errors: 错误队列（FIFO），元素为 ``(code, message)``。
    """

    voltage: float = 0.0
    current: float = DEFAULT_CURRENT
    errors: list[tuple[int, str]] = field(default_factory=list)

    def push_error(self, code: int, message: str) -> None:
        """压入一条错误到队列尾部。"""
        self.errors.append((code, message))

    def pop_error(self) -> tuple[int, str]:
        """弹出错误队列首条；队列为空时返回无错误。"""
        if self.errors:
            return self.errors.pop(0)
        return (0, "No error")

    def reset(self) -> None:
        """复位设备状态（``*RST``）：设定值回到默认。"""
        self.voltage = 0.0
        self.current = DEFAULT_CURRENT
        self.errors.clear()


def handle_command(
    session: ReflectSession, line: str, identity: str = DEFAULT_IDENTITY
) -> str | None:
    """处理一条 SCPI 命令，返回响应文本（无响应返回 ``None``）。

    纯函数式处理（除就地更新 ``session`` 外无副作用），便于单测直接调用。

    Args:
        session: 当前连接会话状态（就地更新）。
        line: 收到的单行命令（可不含换行）。
        identity: ``*IDN?`` 的仪器标识。

    Returns:
        响应字符串（不含换行）；写命令返回 ``None``。
    """
    raw = line.strip()
    if not raw:
        return None

    upper = raw.upper()

    # ── 通用命令 ──────────────────────────────────────────────────────────
    if upper == "*IDN?":
        return identity
    if upper == "*OPC?":
        return "1"
    if upper in ("*RST", "*CLS"):
        if upper == "*RST":
            session.reset()
        else:
            session.errors.clear()
        return None
    if upper in ("SYSTEM:ERROR?", "SYST:ERR?"):
        code, message = session.pop_error()
        return f'{code:+d},"{message}"'

    # ── 设定 / 测量 ───────────────────────────────────────────────────────
    match = _RE_SET_VOLTAGE.match(upper)
    if match:
        session.voltage = float(match.group(1))
        return None

    match = _RE_SET_CURRENT.match(upper)
    if match:
        session.current = float(match.group(1))
        return None

    if _RE_MEAS_VOLTAGE.match(upper):
        return f"{session.voltage:.6f}"
    if _RE_MEAS_CURRENT.match(upper):
        return f"{session.current:.6f}"

    # ── 无法识别 ──────────────────────────────────────────────────────────
    session.push_error(-113, "Undefined header")
    if upper.endswith("?"):
        return '-113,"Undefined header"'
    return None


class SCPIReflectServer:
    """多会话并发的 SCPI 反射服务器（每连接一条独立会话）。

    Attributes:
        host: 监听地址。
        port: 监听端口（构造传 ``0`` 时由系统分配，绑定后从 :attr:`port` 读取）。
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        *,
        identity: str = DEFAULT_IDENTITY,
        log_path: str | os.PathLike[str] | None = None,
    ) -> None:
        """初始化服务器。

        Args:
            host: 监听地址。
            port: 监听端口；``0`` 表示由系统分配临时端口。
            identity: ``*IDN?`` 应答的仪器标识。
            log_path: 可选报文日志（JSON Lines，逐条记录命令/响应/连接号/时刻）。
        """
        self.host = host
        self.port = port
        self.identity = identity
        self._log_path = Path(log_path) if log_path else None
        self._log_fp: TextIO | None = None
        self._log_lock = threading.Lock()
        self._seq = 0

        self._sock: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._conn_seq = 0
        self._conn_lock = threading.Lock()
        self.connections_served = 0

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def start(self) -> "SCPIReflectServer":
        """绑定端口并启动接收线程（非阻塞）。

        Returns:
            自身（便于链式调用）。

        Raises:
            OSError: 端口占用或绑定失败（fail-fast）。
        """
        if self._log_path is not None:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_fp = self._log_path.open("w", encoding="utf-8")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(16)
        sock.settimeout(0.5)
        self.port = sock.getsockname()[1]
        self._sock = sock

        self._stop.clear()
        self._accept_thread = threading.Thread(
            target=self._accept_loop, name="scpi-reflect-accept", daemon=True
        )
        self._accept_thread.start()
        return self

    def stop(self) -> None:
        """停止接收并关闭监听（幂等、干净退出）。"""
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=3.0)
            self._accept_thread = None
        if self._log_fp is not None:
            with self._log_lock:
                self._log_fp.close()
                self._log_fp = None

    def __enter__(self) -> "SCPIReflectServer":
        return self.start()

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.stop()

    # ------------------------------------------------------------------
    # 接收循环
    # ------------------------------------------------------------------
    def _accept_loop(self) -> None:
        """接收连接；每条连接交由独立线程处理。"""
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                conn, _addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break  # 监听套接字已关闭
            with self._conn_lock:
                self._conn_seq += 1
                conn_id = self._conn_seq
            thread = threading.Thread(
                target=self._serve_connection,
                args=(conn, conn_id),
                name=f"scpi-reflect-conn-{conn_id}",
                daemon=True,
            )
            thread.start()

    def _serve_connection(self, conn: socket.socket, conn_id: int) -> None:
        """服务单条连接：按行读取命令，逐条应答。"""
        session = ReflectSession()
        with self._conn_lock:
            self.connections_served += 1
        try:
            reader = conn.makefile("rb")
            try:
                for raw in reader:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line:
                        continue
                    response = handle_command(session, line, self.identity)
                    self._log_record(conn_id, line, response)
                    if response is not None:
                        conn.sendall((response + "\n").encode("utf-8"))
            finally:
                reader.close()
        except OSError:
            # 客户端主动断开是正常路径
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # 报文日志
    # ------------------------------------------------------------------
    def _log_record(self, conn_id: int, command: str, response: str | None) -> None:
        """把一条命令/响应写入 JSON Lines 日志（无日志文件时为无操作）。"""
        if self._log_fp is None:
            return
        with self._log_lock:
            self._seq += 1
            record = {
                "seq": self._seq,
                "ts": round(time.time(), 6),
                "conn_id": conn_id,
                "command": command,
                "response": response,
            }
            self._log_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._log_fp.flush()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：启动反射服务器并阻塞至 ``Ctrl-C``。

    Args:
        argv: 命令行参数；``None`` 时取 ``sys.argv[1:]``。

    Returns:
        退出码（正常收到 ``Ctrl-C`` 返回 0）。
    """
    parser = argparse.ArgumentParser(description="SCPI 反射服务器（真机替代）")
    parser.add_argument(
        "--host", default=os.environ.get(ENV_HOST, DEFAULT_HOST), help="监听地址"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get(ENV_PORT, DEFAULT_PORT)),
        help="监听端口（默认 5025）",
    )
    parser.add_argument(
        "--identity",
        default=os.environ.get(ENV_IDENTITY, DEFAULT_IDENTITY),
        help="*IDN? 应答标识",
    )
    parser.add_argument(
        "--log",
        default=os.environ.get(ENV_LOG),
        help="报文日志文件（JSON Lines），缺省不记录",
    )
    args = parser.parse_args(argv)

    server = SCPIReflectServer(
        host=args.host, port=args.port, identity=args.identity, log_path=args.log
    )
    server.start()
    print(f"SCPI reflect server listening on {server.host}:{server.port}", flush=True)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("SCPI reflect server shutting down", flush=True)
    finally:
        server.stop()
    return 0


__all__ = [
    "SCPIReflectServer",
    "ReflectSession",
    "handle_command",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_IDENTITY",
    "DEFAULT_CURRENT",
    "ENV_PORT",
    "ENV_HOST",
    "ENV_IDENTITY",
    "ENV_LOG",
]


if __name__ == "__main__":
    raise SystemExit(main())
