# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

"""Builders for gesture-injection frames.

A host describes each 30 Hz device cycle as a ``GestureFrame`` — any mix of
discrete gestures and analog overrides (touch position, pressure, orientation).
One or more frames are wrapped in a ``MouthwareMessage`` ready to serialize and
send (see :mod:`mouthpad_gestural_interface.sender`).

All override fields are optional: a frame that only sets ``touch_point`` moves
the cursor while the device keeps deriving everything else; a frame that only
sets ``pressure`` offsets the barometer channel; and so on. Whatever a frame
leaves unset, the device measures for itself that cycle.
"""
from ._pb import Gestures_pb2 as G
from ._pb import GestureInject_pb2 as GI
from ._pb import MouthwareMessage_pb2 as MM

# Sector centres in the raw 1024x768 capacitive frame: raw x grows toward the
# user's left (West), raw y toward the rostrum (North).
SECTOR_CENTER = {
    "N":  (500, 690),
    "NE": (180, 620),
    "E":  (160, 360),
    "SE": (195, 150),
    "S":  (525, 130),
    "SW": (845, 175),
    "W":  (870, 380),
    "NW": (835, 630),
    "CENTER": (512, 384),
}


def touch_frame(x, y):
    """A frame overriding the resolved tongue touch to raw ``(x, y)``."""
    f = GI.GestureFrame()
    f.touch_point.x = int(x)
    f.touch_point.y = int(y)
    return f


def sector_frame(sector):
    """A touch frame at the centre of a named sector (see ``SECTOR_CENTER``)."""
    x, y = SECTOR_CENTER[sector]
    return touch_frame(x, y)


def no_touch_frame():
    """A frame carrying an explicit NO_TOUCH touchpad gesture (lift-off)."""
    f = GI.GestureFrame()
    g = f.gestures.add()
    g.source = G.GS_TOUCHPAD
    g.touchpad_gesture_type = G.TGT_NO_TOUCH
    g.gesture_duration_cycles = 1
    return f


def custom_gesture_frame(source, gesture_type=None, gesture_subtype=None, duration_cycles=1):
    """A frame carrying one custom gesture, given by the indices a profile's
    ``customGestures`` table assigns its names.

    ``source`` is the custom source index (10 or above). A type or subtype left
    as None is omitted from the gesture.
    """
    f = GI.GestureFrame()
    g = f.gestures.add()
    g.custom_gesture_source = int(source)
    if gesture_type is not None:
        g.custom_gesture_type = int(gesture_type)
    if gesture_subtype is not None:
        g.custom_gesture_subtype = int(gesture_subtype)
    g.gesture_duration_cycles = int(duration_cycles)
    return f


def pressure_frame(value):
    """A frame overriding the measured barometer pressure with a raw value."""
    f = GI.GestureFrame()
    f.pressure = float(value)
    return f


def quaternion_frame(w, x, y, z):
    """A frame overriding the IMU-fused orientation delta for this cycle."""
    f = GI.GestureFrame()
    f.q_delta.w, f.q_delta.x, f.q_delta.y, f.q_delta.z = (
        float(w), float(x), float(y), float(z))
    return f


def set_touch(frame, x, y):
    frame.touch_point.x = int(x)
    frame.touch_point.y = int(y)
    return frame


def set_pressure(frame, value):
    frame.pressure = float(value)
    return frame


def set_quaternion(frame, w, x, y, z):
    frame.q_delta.w, frame.q_delta.x, frame.q_delta.y, frame.q_delta.z = (
        float(w), float(x), float(y), float(z))
    return frame


def play_gesture_vector(frames):
    """Wrap frames in a ``MouthwareMessage`` ready to serialize and send.

    An empty ``frames`` cancels any in-flight playback on the device.
    """
    msg = MM.MouthwareMessage()
    msg.developer_test_io_command.play_gesture_vector.frames.extend(frames)
    return msg
