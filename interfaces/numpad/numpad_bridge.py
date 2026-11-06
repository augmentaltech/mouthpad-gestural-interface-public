#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.
"""Drive a MouthPad's FSM from the numpad.

Maps key presses to virtual gestures and streams them to the device as framed
PlayGestureVector messages over the USB-CDC side-band (auto-detected), with
mouthpad_gestural_interface.

Key map (numpad, NumLock on)
  7 8 9          (hold)   NW  N  NE
  4   6                   W      E
  1 2 3                   SW  S  SE
  Enter          (hold)   raise pressure above baseline; release -> baseline
  +              (hold)   lower pressure below baseline;  release -> baseline
  Ctrl-C                  quit

Every held key streams one frame per tick reflecting the current input: a touch
point (or NO_TOUCH) on the touchpad channel and a raw barometer pressure value.
Both are analog overrides — the firmware replaces its measured pressure /
estimated touch with these and runs the real gesture + cursor pipeline — so a
held direction moves the cursor and a held Enter/+ offsets the pressure.

Needs pynput for global key capture:  pip install -r requirements.txt

    python numpad_bridge.py                # auto-detect the port
    python numpad_bridge.py --hz 50 --flip-ns
"""
import argparse
import random
import sys
import threading
import time

from mouthpad_gestural_interface import (
    GestureSender, no_touch_frame, sector_frame, set_pressure,
)

# Injected raw barometer pressure (frame.pressure overrides the measured value).
PRESSURE_BASELINE = 1000.0
PRESSURE_DELTA = {"press": 50.0, "sip": -50.0}
PRESSURE_NOISE = 0.05  # +/- uniform

# Numpad digit -> sector, laid out as the keys sit on the pad.
NUMPAD_SECTOR = {
    "7": "NW", "8": "N", "9": "NE",
    "4": "W",            "6": "E",
    "1": "SW", "2": "S",  "3": "SE",
}

# --flip-ns swaps the vertical axis if the pad's north turns out to be the
# numpad's south.
NS_FLIP = {"N": "S", "S": "N", "NE": "SE", "SE": "NE", "NW": "SW", "SW": "NW"}
FLIP_NS = False

# A numpad key arrives as a plain digit char when NumLock is on, but some
# platforms/layouts only give the virtual-key code, so accept those too:
# X11 XK_KP_0..9 = 65456..65465, Windows/evdev VK_NUMPAD0..9 = 96..105.
_VK_DIGIT = {**{65456 + n: str(n) for n in range(10)},
             **{96 + n: str(n) for n in range(10)}}
_VK_KP_ADD = (65451, 107)  # XK_KP_Add, VK_ADD


def key_digit(key):
    """'1'..'9' for a numpad (or top-row) digit key, else None."""
    ch = getattr(key, "char", None)
    if ch in NUMPAD_SECTOR:
        return ch
    d = _VK_DIGIT.get(getattr(key, "vk", None))
    return d if d in NUMPAD_SECTOR else None


def is_plus(key):
    return getattr(key, "char", None) == "+" or getattr(key, "vk", None) in _VK_KP_ADD


def resolve_sector(held):
    """Sector for the most recently pressed still-held digit; None if none held."""
    if not held:
        return None
    sector = NUMPAD_SECTOR[held[-1]]
    return NS_FLIP.get(sector, sector) if FLIP_NS else sector


def _pressure_value(mode):
    """Raw barometer value for a pressure mode (None|'press'|'sip'), with jitter."""
    target = PRESSURE_BASELINE + PRESSURE_DELTA.get(mode, 0.0)
    return target + random.uniform(-PRESSURE_NOISE, PRESSURE_NOISE)


def build_state(sector, pressure_mode):
    """One frame reflecting the currently-held input: a touch point (or NO_TOUCH)
    plus a raw pressure value. A NO_TOUCH + baseline-pressure frame
    (sector=None, pressure_mode=None) returns the FSM to rest."""
    f = sector_frame(sector) if sector is not None else no_touch_frame()
    set_pressure(f, _pressure_value(pressure_mode))
    return f


class Injector:
    def __init__(self, sender, hz, kb):
        self.sender = sender
        self.period = 1.0 / hz
        self.kb = kb
        self.held = []  # digit keys in press order; the last one wins
        self.pressure = None  # None | 'press' | 'sip', held between keydown/keyup
        self.lock = threading.Lock()
        self.running = True
        self.last_sector = None
        self.last_pressure = None
        self.was_active = False

    def on_press(self, key):
        digit = key_digit(key)
        with self.lock:
            if digit is not None:
                if digit in self.held:
                    self.held.remove(digit)
                self.held.append(digit)
            elif key == self.kb.Key.enter:
                self.pressure = "press"
            elif is_plus(key):
                self.pressure = "sip"

    def on_release(self, key):
        digit = key_digit(key)
        with self.lock:
            if digit is not None:
                if digit in self.held:
                    self.held.remove(digit)
            elif key == self.kb.Key.enter or is_plus(key):
                self.pressure = None

    def run(self):
        next_t = time.perf_counter()
        while self.running:
            with self.lock:
                sector = resolve_sector(self.held)
                pressure = self.pressure
            active = sector is not None or pressure is not None
            if active:
                self.sender.send([build_state(sector, pressure)])
            elif self.was_active:
                self.sender.send([build_state(None, None)])
            if sector != self.last_sector or pressure != self.last_pressure:
                self._log_state(sector, pressure)
            self.last_sector, self.last_pressure, self.was_active = sector, pressure, active
            next_t += self.period
            dt = next_t - time.perf_counter()
            if dt > 0:
                time.sleep(dt)
            else:
                next_t = time.perf_counter()

    @staticmethod
    def _log_state(sector, pressure):
        parts = []
        if sector is not None:
            parts.append(f"touch {sector}")
        if pressure is not None:
            parts.append(pressure)
        print(" + ".join(parts) if parts else "release")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=None, help="side-band serial port (auto-detected if a single side-band port is present)")
    ap.add_argument("--hz", type=float, default=50.0, help="touch-frame stream rate while a direction key is held")
    ap.add_argument("--flip-ns", action="store_true", help="swap north/south if the pad's north reads as the numpad's south")
    args = ap.parse_args()

    global FLIP_NS
    FLIP_NS = args.flip_ns

    try:
        from pynput import keyboard
    except ImportError:
        print("ERROR: pynput not installed. Run: pip install -r requirements.txt", file=sys.stderr)
        return 2

    try:
        sender = GestureSender(port=args.port)
    except RuntimeError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 2

    print(f"\nUSB: {sender.port}")
    print("numpad 1-9 = touch (hold; 8=N 2=S 4=W 6=E, corners = diagonals, NumLock on)"
          f"{' [N/S flipped]' if FLIP_NS else ''}")
    print("Enter = click | + = sip | Ctrl-C = quit\n")

    inj = Injector(sender, args.hz, keyboard)
    listener = keyboard.Listener(on_press=inj.on_press, on_release=inj.on_release)
    listener.start()
    try:
        inj.run()
    except KeyboardInterrupt:
        pass
    finally:
        inj.running = False
        listener.stop()
        sender.close()
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
