#!/usr/bin/env python3
"""Read VAB sample manipulator positions once (or poll until interrupted).

Usage:
    python read_positions.py --port COM5 [--period 2]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
s
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vab_manipulator import DEFAULT_BAUD, UNITS, VABManipulator


def main() -> None:
    parser = argparse.ArgumentParser(description="Read VAB positions.")
    parser.add_argument("--port", default=os.environ.get("VAB_PORT"),
                        help="Serial port (or set VAB_PORT).")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--period", type=float, default=0.0,
                        help="If > 0, poll every PERIOD seconds.")
    args = parser.parse_args()
    if not args.port:
        parser.error("serial port required (--port or VAB_PORT)")

    with VABManipulator(port=args.port, baud=args.baud) as stage:
        while True:
            for axis, value in stage.read_positions().items():
                print(f"  {axis}: {value:.2f} {UNITS[axis]}")
            if args.period <= 0:
                break
            print("---")
            try:
                time.sleep(args.period)
            except KeyboardInterrupt:
                break


if __name__ == "__main__":
    main()
