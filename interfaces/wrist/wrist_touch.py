#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.
"""Wrist pose -> synthetic tongue touch -> cursor velocity.

The wrist's two angles place a synthetic touch on the MouthPad's touchpad, the
way a tongue held off-centre does: waving the hand to the side moves the touch
east / west, bending the wrist back or forward moves it north / south. The
standard tongue-mouse profile turns a held off-centre touch into cursor
velocity, so the further the wrist is bent the faster the cursor moves, and a
neutral wrist (within --deadband of the full reach) lifts the touch and stops it.

The two axes have separate ranges because MediaPipe resolves them differently:
a wave to the side turns the fingers across the image, but a bend toward or
away from the camera mostly shows up as a small change in estimated depth, so
the same wrist bend reads as a far smaller lift angle. --lift-range is set
narrower to amplify it; watch the lift readout at a full bend and set it to
about that.

Load the standard MouthPad profile in tongue control mode first.

    python wrist_touch.py [--side-range 30] [--lift-range 10] [--deadband 0.2] [--dry-run]
"""
import argparse
import random
import sys

from mouthpad_gestural_interface import no_touch_frame, set_pressure, touch_frame

from wrist_pose import add_common_args, run

# The raw touch frame is 1024 x 768 with x growing toward the user's left
# (West) and y toward the rostrum (North).
CENTER = (512, 384)
REACH = (360, 300)

# Held barometer reading, with jitter so the value is never perfectly static.
PRESSURE_BASELINE = 1000.0
PRESSURE_NOISE = 0.05


def touch_point_for(side, lift, side_range, lift_range, deadband):
    """Raw (x, y) touch for wrist angles, or None inside the deadband.

    ``side_range`` / ``lift_range`` degrees reach the edge of the touch area on
    each axis; more is clamped. ``deadband`` is the fraction of that reach that
    still counts as neutral, so it is the same on both axes however narrow the
    lift range is.
    """
    u = max(-1.0, min(1.0, side / side_range))
    v = max(-1.0, min(1.0, lift / lift_range))
    if (u * u + v * v) ** 0.5 < deadband:
        return None
    x = round(CENTER[0] - u * REACH[0])
    y = round(CENTER[1] + v * REACH[1])
    return max(0, min(1023, x)), max(0, min(767, y))


def frame_for(angles, side_range, lift_range, deadband):
    point = None if angles is None else touch_point_for(*angles, side_range, lift_range, deadband)
    f = no_touch_frame() if point is None else touch_frame(*point)
    set_pressure(f, PRESSURE_BASELINE + random.uniform(-PRESSURE_NOISE, PRESSURE_NOISE))
    return f, point


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--side-range", type=float, default=30.0,
                    help="degrees of side-to-side wave for a full-reach east / west touch")
    ap.add_argument("--lift-range", type=float, default=10.0,
                    help="degrees of measured lift for a full-reach north / south touch; MediaPipe reads a wrist "
                         "bend toward or away from the camera as a much smaller angle, so this is narrower")
    ap.add_argument("--deadband", type=float, default=0.2,
                    help="fraction of the full reach that still counts as neutral")
    add_common_args(ap)
    args = ap.parse_args()

    def step(angles):
        f, point = frame_for(angles, args.side_range, args.lift_range, args.deadband)
        if angles is None:
            return [f], ""
        status = f"side {angles[0]:+5.1f}  lift {angles[1]:+5.1f}  ->  "
        return [f], status + ("no touch" if point is None else f"touch {point}")

    try:
        run(args, step)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
