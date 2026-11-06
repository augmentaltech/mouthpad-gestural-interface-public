# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

"""USB transport for gesture injection.

Frames a serialized ``MouthwareMessage`` with a 2-byte little-endian length
prefix and writes it to the hardware key's USB serial port. ``GestureSender``
finds the port and is a context manager:

    from mouthpad_gestural_interface import GestureSender, sector_frame

    with GestureSender() as dev:                 # auto-detects the port
        dev.send([sector_frame("N")])            # one cycle: touch North
        dev.send([])                             # release / cancel playback
"""
import struct

import serial
import serial.tools.list_ports

from .frames import play_gesture_vector

BAUD = 115200
NORDIC_VID = 0x1915

# The hardware key exposes two USB serial ports: log text and the proto
# side-band. These are the side-band's communication and data interface numbers.
PROTO_CDC_INTERFACES = {2, 3}


def _usb_interface(port):
    """Interface number from a location like '1-1:1.2' (Linux) or '1-1:x.2' (Windows)."""
    loc = port.location or ""
    if ":" not in loc:
        return None
    tail = loc.rsplit(".", 1)[-1]
    return int(tail) if tail.isdigit() else None


def side_band_ports(ports):
    """Device paths of the hardware keys' side-band ports among ``ports``.

    macOS reports no interface number, but names each port after it, so there
    the later-named of a key's two ports is its side-band.
    """
    out = []
    unnumbered = {}
    for p in ports:
        if p.vid != NORDIC_VID:
            continue
        iface = _usb_interface(p)
        if iface is None:
            unnumbered.setdefault(p.serial_number, []).append(p.device)
        elif iface in PROTO_CDC_INTERFACES:
            out.append(p.device)
    out.extend(max(devices) for devices in unnumbered.values())
    return out


def list_side_band_ports():
    """Device paths of every attached hardware key's side-band port."""
    return side_band_ports(serial.tools.list_ports.comports())


def frame_bytes(msg):
    """Length-prefixed wire bytes for a MouthwareMessage."""
    payload = msg.SerializeToString()
    if len(payload) > 0xFFFF:
        raise ValueError(f"payload {len(payload)}B exceeds the 2-byte length prefix")
    return struct.pack("<H", len(payload)) + payload


class GestureSender:
    def __init__(self, port=None, baud=BAUD):
        """Open the hardware key's side-band port.

        ``port`` is auto-detected when omitted, if exactly one key is attached.
        """
        if port is None:
            found = list_side_band_ports()
            if len(found) != 1:
                raise RuntimeError(
                    f"expected exactly one hardware key, found {len(found)}; "
                    f"pass port=... explicitly ({found})")
            port = found[0]
        self.port = port
        self.ser = serial.Serial(port, baud, timeout=1)

    def send_message(self, msg):
        """Frame and write a MouthwareMessage, then flush."""
        self.ser.write(frame_bytes(msg))
        self.ser.flush()

    def send(self, frames):
        """Frame and write a PlayGestureVector of the given GestureFrames.

        An empty list cancels any in-flight playback on the device.
        """
        self.send_message(play_gesture_vector(frames))

    def close(self):
        if self.ser is not None:
            self.ser.close()
            self.ser = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
