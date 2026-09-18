"""VAB 4-axis sample manipulator position readout over RS-232 (pyserial).

Hardware
--------
A VAB UHV three-axis sample manipulator stage -- used in the lab as a
thin-film sample stage in a vacuum chamber -- with X/Y/Z plus rotation
position readout. No official protocol documentation was available: the
position query below was reverse-engineered with a serial monitor against
the official VAB manipulator program.

What this module does
---------------------
Read-only position polling:

* send the position query ``b"<_1001100000000000000000000000_>"``,
* read the reply up to the ``b"_>"`` terminator,
* parse per-axis 9-character step counts (``<_3001<axis><steps>``),
* convert steps to mm / degrees with the lab's scale factors.

No move commands are implemented: in the lab workflow the stage is moved
manually (or via the vendor program) and this code only reads positions.

Communication
-------------
RS-232 serial, 19200 baud 8N1, 1 s timeout. DTR and RTS are deasserted so
USB-serial bridges do not reset the controller.

Prerequisites
-------------
* Python packages: ``pyserial``.
* The serial port name (e.g. ``COM5`` on Windows, ``/dev/ttyUSB0`` on Linux).

Importing this module never touches hardware. The port is opened only by
``VABManipulator.connect()`` / the context manager.
"""

from __future__ import annotations

import re
import time

try:
    import serial
except ImportError as exc:  # pragma: no cover - import guard
    serial = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

DEFAULT_BAUD = 19200
DEFAULT_TIMEOUT_S = 1.0
POSITION_QUERY = b"<_1001100000000000000000000000_>"
REPLY_TERMINATOR = b"_>"
#: Reply chunk: <_3001 <axis 01..04> <9-char step count> ...
POSITION_RE = re.compile(r"<_3001(0[1-4])(.{9})")
AXIS_LABELS = {"01": "X", "02": "Y", "03": "Z", "04": "Rotation"}
#: Hardware-specific step scaling (steps per mm, steps per degree).
SCALE_FACTORS = {"X": 800 / 3, "Y": 800 / 3, "Z": 500 / 3, "Rotation": 50.0}
UNITS = {"X": "mm", "Y": "mm", "Z": "mm", "Rotation": "deg"}


def _require_serial():
    if serial is None:
        raise RuntimeError(
            f"pyserial is required to talk to the VAB controller ({_IMPORT_ERROR}). "
            "Install it with: pip install pyserial"
        )
    return serial


# ---------------------------------------------------------------------------
# Pure helpers (no hardware needed; safe to unit-test)
# ---------------------------------------------------------------------------

def parse_positions(reply: str) -> dict[str, int]:
    """Parse raw axis step counts from a controller reply string.

    Returns e.g. ``{"X": 12345, "Y": -40, ...}``. Raises ``ValueError`` when
    the reply contains no recognizable position chunks.
    """
    matches = POSITION_RE.findall(reply)
    if not matches:
        raise ValueError(f"No VAB position data in reply: {reply!r}")
    positions = {}
    for axis, value in matches:
        positions[AXIS_LABELS[axis]] = int(value)
    return positions


def to_physical_units(raw_steps: dict[str, int]) -> dict[str, float]:
    """Convert raw step counts to mm / degrees via :data:`SCALE_FACTORS`."""
    return {
        label: steps / SCALE_FACTORS[label]
        for label, steps in raw_steps.items()
    }


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class VABManipulator:
    """Read-only client for the VAB sample manipulator controller.

    Example::

        with VABManipulator(port="COM5") as stage:  # your port here
            print(stage.read_positions())
    """

    def __init__(self, port: str, baud: int = DEFAULT_BAUD,
                 timeout: float = DEFAULT_TIMEOUT_S, serial_factory=None):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self._serial_factory = serial_factory
        self._ser = None

    def connect(self) -> "VABManipulator":
        """Open the port with DTR/RTS deasserted (no bridge reset)."""
        if self._ser is not None:
            return self
        factory = self._serial_factory
        if factory is None:
            factory = _require_serial().Serial
        self._ser = factory(port=self.port, baudrate=self.baud,
                            timeout=self.timeout)
        # Prevent the USB bridge from triggering a hardware reset.
        self._ser.dtr = False
        self._ser.rts = False
        time.sleep(0.2)
        self._ser.reset_input_buffer()
        return self

    def close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def __enter__(self) -> "VABManipulator":
        return self.connect()

    def __exit__(self, *exc) -> None:
        self.close()

    def read_positions(self) -> dict[str, float]:
        """Query and return ``{"X": mm, "Y": mm, "Z": mm, "Rotation": deg}``."""
        if self._ser is None:
            raise RuntimeError("Not connected; call connect() first")
        self._ser.reset_input_buffer()
        self._ser.write(POSITION_QUERY)
        self._ser.flush()
        reply = self._ser.read_until(REPLY_TERMINATOR).decode(
            "utf-8", errors="ignore")
        if "<_3001" not in reply:
            raise ValueError(f"Unexpected VAB response: {reply!r}")
        return to_physical_units(parse_positions(reply))
