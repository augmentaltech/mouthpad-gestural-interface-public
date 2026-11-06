# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

"""MouthPad gestural interface.

A small, self-contained library for sending gestures and raw sensor overrides
directly to a MouthPad device over the USB-CDC side-band. The wire format is the
device's own protobuf (a reduced, wire-compatible subset lives in ``src/proto``)
— there is no translation layer.

Typical use::

    from mouthpad_gestural_interface import GestureSender, sector_frame, pressure_frame

    with GestureSender() as dev:
        dev.send([sector_frame("N")])          # touch the North sector
        dev.send([pressure_frame(1050.0)])     # raise barometer pressure
        dev.send([])                           # release

For lower-level control, build ``GestureFrame`` / ``MouthwareMessage`` objects
via :mod:`mouthpad_gestural_interface.frames` and the raw protobuf modules under
``mouthpad_gestural_interface._pb``.
"""
from .frames import (
    SECTOR_CENTER,
    custom_gesture_frame,
    no_touch_frame,
    play_gesture_vector,
    pressure_frame,
    quaternion_frame,
    sector_frame,
    set_pressure,
    set_quaternion,
    set_touch,
    touch_frame,
)
from .sender import (
    BAUD,
    GestureSender,
    frame_bytes,
    list_side_band_ports,
)

__all__ = [
    "GestureSender",
    "SECTOR_CENTER",
    "BAUD",
    "frame_bytes",
    "list_side_band_ports",
    "play_gesture_vector",
    "touch_frame",
    "sector_frame",
    "no_touch_frame",
    "custom_gesture_frame",
    "pressure_frame",
    "quaternion_frame",
    "set_touch",
    "set_pressure",
    "set_quaternion",
]
