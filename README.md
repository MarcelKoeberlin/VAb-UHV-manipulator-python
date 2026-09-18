# VAB UHV manipulator readout (Python, via serial)

Read-only position polling for a **VAB UHV three-axis sample manipulator**
(X/Y/Z plus rotation readout): send the position query, parse per-axis step
counts, convert to mm / degrees.

Extracted from tested, working laboratory control software. Tested on
Windows only; other platforms are unverified.

## Hardware

- VAB UHV three-axis manipulator (used in the lab as a thin-film sample
  stage in a vacuum chamber), with X/Y/Z plus rotation position readout.
- The protocol was reverse-engineered with a serial monitor against the
  official VAB manipulator program, since no official protocol documentation
  was available.

- Communication: **RS-232 serial**, 19200 baud 8N1. Query
  `<_1001100000000000000000000000_>`, reply terminated by `_>`, per-axis
  chunks `<_3001<axis><9-char steps>` with axes 01=X, 02=Y, 03=Z, 04=Rot.
- Step scales: X/Y 800/3 steps/mm, Z 500/3 steps/mm, rotation 50 steps/deg.

## Supported operations

- Read all four axis positions (mm / degrees)

Moves are intentionally not implemented: in the lab workflow the stage is
positioned manually (or via the vendor program) and this code only reads
positions. No move-command syntax is known.

## Prerequisites

- Python 3.9+ with a project-local environment:

```bash
python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements.txt  # just pyserial
```
- Serial port name (`COM5` on Windows, `/dev/ttyUSB0` on Linux)

## Usage

```python
from vab_manipulator import VABManipulator

with VABManipulator(port="COM5") as stage:  # your port here
    print(stage.read_positions())
    # {'X': 45.0, 'Y': -15.0, 'Z': 30.0, 'Rotation': 90.0}
```

```bash
export VAB_PORT=COM5
python examples/read_positions.py
python examples/read_positions.py --period 2   # poll every 2 s
```

Importing `vab_manipulator` never touches hardware; the port opens only in
`connect()` / the context manager. DTR/RTS are deasserted so USB-serial
bridges do not reset the controller.

## Limitations

- Move, homing, and limit behavior are unknown (read-only protocol).
- Step scales and axis mapping are installation-specific: confirm against a
  known displacement on your stage.

## Tests

Hardware-free unit tests use a fake serial port:

```bash
pip install pytest
pytest -q
```
