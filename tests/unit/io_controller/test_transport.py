"""Unit tests for hive.io_controller.transport."""

from __future__ import annotations

import threading
import time

import pytest

from hive.io_controller.transport import (
    HiveIOTransport,
    LoopbackTransport,
    SerialTransport,
    TransportError,
)


class TestLoopbackTransport:
    def test_create_pair_yields_two_linked_transports(self):
        a, b = LoopbackTransport.create_pair()
        assert isinstance(a, LoopbackTransport)
        assert isinstance(b, LoopbackTransport)
        assert a.is_open and b.is_open

    def test_write_then_read_roundtrip(self):
        a, b = LoopbackTransport.create_pair()
        a.write_line(b'{"hello": "from a"}')
        assert b.read_line(1.0) == b'{"hello": "from a"}'

    def test_write_adds_trailing_newline_if_missing(self):
        a, b = LoopbackTransport.create_pair()
        a.write_line(b'{"k": 1}')
        # Even though we wrote without \n, peer sees the line
        assert b.read_line(1.0) == b'{"k": 1}'

    def test_write_keeps_trailing_newline(self):
        a, b = LoopbackTransport.create_pair()
        a.write_line(b'{"k": 1}\n')
        # Transport strips trailing \n for the reader (returns just the line)
        assert b.read_line(1.0) == b'{"k": 1}'

    def test_bidirectional(self):
        a, b = LoopbackTransport.create_pair()
        a.write_line(b"msg from a")
        b.write_line(b"msg from b")
        assert a.read_line(1.0) == b"msg from b"
        assert b.read_line(1.0) == b"msg from a"

    def test_read_timeout_returns_none(self):
        _a, b = LoopbackTransport.create_pair()
        # Nothing was written → read returns None quickly
        start = time.monotonic()
        result = b.read_line(0.1)
        elapsed = time.monotonic() - start
        assert result is None
        assert elapsed < 0.5  # should be ~0.1s

    def test_close_blocks_writes(self):
        a, _b = LoopbackTransport.create_pair()
        a.close()
        with pytest.raises(TransportError):
            a.write_line(b"msg")

    def test_close_blocks_reads(self):
        _a, b = LoopbackTransport.create_pair()
        b.close()
        with pytest.raises(TransportError):
            b.read_line(0.1)

    def test_is_open_property(self):
        a, _b = LoopbackTransport.create_pair()
        assert a.is_open
        a.close()
        assert not a.is_open

    def test_thread_safety(self):
        a, b = LoopbackTransport.create_pair()

        # Cross-thread write+read smoke test
        def writer():
            for i in range(50):
                a.write_line(f"msg-{i}".encode())

        def reader():
            count = 0
            while count < 50:
                line = b.read_line(0.5)
                if line is not None:
                    count += 1

        t_write = threading.Thread(target=writer, daemon=True)
        t_read = threading.Thread(target=reader, daemon=True)
        t_write.start()
        t_read.start()
        t_write.join(timeout=5.0)
        t_read.join(timeout=5.0)


class TestSerialTransportImportGuard:
    def test_construction_does_not_require_pyserial(self):
        # Construction should succeed even without pyserial.
        t = SerialTransport(port="/dev/null", baudrate=115200)
        assert t.is_open is False

    def test_open_without_pyserial_raises(self, monkeypatch):
        # Force pyserial import to fail
        import builtins as _bi

        original_import = _bi.__import__

        def mock_import(name, *args, **kwargs):
            if name == "serial" or name.startswith("serial."):
                raise ImportError("simulated pyserial missing")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(_bi, "__import__", mock_import)
        t = SerialTransport(port="/dev/null", baudrate=115200)
        with pytest.raises(TransportError):
            t.open()

    def test_close_is_safe_when_not_open(self):
        t = SerialTransport(port="/dev/null", baudrate=115200)
        # Should not raise
        t.close()
        assert t.is_open is False

    def test_write_without_open_raises(self):
        t = SerialTransport(port="/dev/null", baudrate=115200)
        with pytest.raises(TransportError):
            t.write_line(b"data")

    def test_read_without_open_raises(self):
        t = SerialTransport(port="/dev/null", baudrate=115200)
        with pytest.raises(TransportError):
            t.read_line(1.0)


class TestHiveIOTransportABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            HiveIOTransport()  # type: ignore[abstract]
