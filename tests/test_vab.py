"""Hardware-free tests for the VAB client using a fake serial port."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from vab_manipulator import (
    POSITION_QUERY,
    VABManipulator,
    parse_positions,
    to_physical_units,
)

SAMPLE_REPLY = "<_300101+00012000_><_300102-00004000_><_300103+00005000_><_300104+00004500_>"


def test_parse_positions():
    assert parse_positions(SAMPLE_REPLY) == {
        "X": 12000, "Y": -4000, "Z": 5000, "Rotation": 4500,
    }


def test_parse_positions_rejects_garbage():
    with pytest.raises(ValueError):
        parse_positions("hello")


def test_to_physical_units():
    physical = to_physical_units({"X": 800, "Y": 800, "Z": 500, "Rotation": 50})
    assert physical == {"X": 3.0, "Y": 3.0, "Z": 3.0, "Rotation": 1.0}


class FakeSerial:
    def __init__(self, reply, **kwargs):
        self.reply = reply
        self.written = []
        self.dtr = True
        self.rts = True
        self.closed = False

    def reset_input_buffer(self):
        pass

    def write(self, payload):
        self.written.append(payload)

    def flush(self):
        pass

    def read_until(self, terminator):
        assert terminator == b"_>"
        return self.reply

    def close(self):
        self.closed = True


def test_read_positions_roundtrip():
    factory = lambda **kwargs: FakeSerial(SAMPLE_REPLY.encode(), **kwargs)
    with VABManipulator(port="FAKE", serial_factory=factory) as stage:
        assert stage._ser.dtr is False
        assert stage._ser.rts is False
        positions = stage.read_positions()
    assert stage._ser is None
    assert positions["X"] == pytest.approx(12000 / (800 / 3))
    assert positions["Rotation"] == pytest.approx(90.0)


def test_query_bytes():
    seen = {}

    def factory(**kwargs):
        port = FakeSerial(SAMPLE_REPLY.encode(), **kwargs)
        seen["port"] = port
        return port

    with VABManipulator(port="FAKE", serial_factory=factory) as stage:
        stage.read_positions()
    assert seen["port"].written == [POSITION_QUERY]


def test_requires_connection():
    stage = VABManipulator(port="FAKE")
    with pytest.raises(RuntimeError):
        stage.read_positions()
