#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.
"""Wrist pose -> synthetic IMU rotation -> cursor displacement.

Each camera frame, the change in the wrist's two angles becomes a small
rotation sent as the MouthPad's IMU orientation delta, the way a head turn
would be. The head-mouse profile moves the cursor by an amount proportional to
that rotation, so the cursor follows the hand's position: wave to the side and
it moves sideways, bend the wrist back or forward and it moves up or down, hold
still and it stays put.

Load the standard MouthPad profile in head control mode first.

The firmware's axis convention depends on how the device is lying (its AUTO
head-mouse orientation reads gravity from the real IMU), so --axes picks the
one to target; try another if the cursor's axes come out swapped or reversed.

    python wrist_imu.py [--gain 1.0] [--axes seated] [--dry-run]
"""
import argparse
import math
import random
import sys

from mouthpad_gestural_interface import no_touch_frame, set_pressure, set_quaternion
from mouthpad_gestural_interface._pb import Gestures_pb2 as G

from wrist_pose import add_common_args, run

PRESSURE_BASELINE = 1000.0
PRESSURE_NOISE = 0.05

# (pitch, yaw) in degrees for a (rightward, upward) cursor step, per firmware
# head-mouse orientation. Seated: x follows pitch and y follows -yaw.
# Side-lying capsule up: x = -yaw, y = -pitch. Capsule down: x = yaw, y = pitch.
# Screen y grows downward, so "up" is -y.
AXES = {
    "seated": lambda right, up: (right, up),
    "capsule-up": lambda right, up: (up, -right),
    "capsule-down": lambda right, up: (-up, right),
}

IDENTITY = (1.0, 0.0, 0.0, 0.0)


def q_delta_for(d_side, d_lift, axes="seated"):
    """(w, x, y, z) rotation whose firmware Euler pitch and yaw move the cursor
    right by ``d_side`` and up by ``d_lift`` degrees' worth."""
    pitch, yaw = AXES[axes](d_side, d_lift)
    if pitch == 0 and yaw == 0:
        return IDENTITY
    hp, hy = math.radians(pitch) / 2, math.radians(yaw) / 2
    cp, sp, cy, sy = math.cos(hp), math.sin(hp), math.cos(hy), math.sin(hy)
    # yaw about z applied after pitch about y (the ZYX order Fusion decodes).
    return (cy * cp, -sy * sp, cy * sp, sy * cp)


class Displacement:
    """Per-frame change in wrist angles, scaled by ``gain``."""

    def __init__(self, gain):
        self.gain = gain
        self.previous = None
        self.moving_cycles = 0

    def step(self, angles):
        if angles is None:
            self.previous = None
            self.moving_cycles = 0
            return 0.0, 0.0
        if self.previous is None:
            self.previous = angles
        d = tuple(self.gain * (a - p) for a, p in zip(angles, self.previous))
        self.previous = angles
        self.moving_cycles = self.moving_cycles + 1 if d != (0.0, 0.0) else 0
        return d


def frame_for(d_side, d_lift, axes, moving_cycles):
    """A frame carrying the rotation, the head-movement gesture the firmware
    would derive from it, no touch and baseline pressure."""
    f = no_touch_frame()
    set_pressure(f, PRESSURE_BASELINE + random.uniform(-PRESSURE_NOISE, PRESSURE_NOISE))
    q = q_delta_for(d_side, d_lift, axes)
    set_quaternion(f, *q)
    g = f.gestures.add()
    g.source = G.GS_IMU
    g.imu_gesture_type = G.IGT_HEAD_NO_MOVEMENT if q == IDENTITY else G.IGT_HEAD_MOVEMENT
    g.imu_gesture_subtype = G.IGS_IMU_SUBTYPE_NONE
    g.gesture_duration_cycles = max(1, moving_cycles)
    return f


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gain", type=float, default=1.0, help="degrees of synthetic rotation per degree of wrist bend")
    ap.add_argument("--axes", choices=sorted(AXES), default="seated", help="the firmware head-mouse orientation to target")
    add_common_args(ap)
    args = ap.parse_args()

    displacement = Displacement(args.gain)

    def step(angles):
        d_side, d_lift = displacement.step(angles)
        f = frame_for(d_side, d_lift, args.axes, displacement.moving_cycles)
        if angles is None:
            return [f], ""
        return [f], f"side {angles[0]:+5.1f}  lift {angles[1]:+5.1f}  ->  step {d_side:+4.2f}, {d_lift:+4.2f} deg"

    try:
        run(args, step)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
