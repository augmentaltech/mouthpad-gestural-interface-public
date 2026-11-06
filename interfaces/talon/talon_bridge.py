#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.
"""Drive a MouthPad's press and sip from Talon Voice's two built-in noises.

Talon recognises two non-speech noises out of the box, with no training: a lip
"pop" and a sustained "hiss". The Talon user script in talon-user/ forwards them
as UDP datagrams to this bridge, which streams PlayGestureVector messages to the
device with mouthpad_gestural_interface, over the USB side-band to a MouthPad
hardware key.

Noise map (set in the Talon script)
  pop            (instant)  sip, held for --pulse-ms then released
  hiss           (held)     tongue press, for as long as the hiss lasts
  Ctrl-C                    quit

Datagrams (ASCII, to 127.0.0.1:--udp-port), for either gesture
  press | sip              pulse it for --pulse-ms
  press on | sip on        hold it
  press off | sip off      let go

Talon runs its own embedded Python, so keeping the device link out here means
nothing has to be installed into Talon, and the bridge can be exercised without
it:  echo -n sip | nc -u -w0 127.0.0.1 47700

    python talon_bridge.py                 # auto-detect the port
    python talon_bridge.py --dry-run       # log noises, no device needed
"""
import argparse
import random
import socket
import sys
import threading
import time

from mouthpad_gestural_interface import (
    SECTOR_CENTER, GestureSender, no_touch_frame, set_pressure, touch_frame)

UDP_PORT = 47700

# Injected raw barometer pressure (frame.pressure overrides the measured value).
PRESSURE_BASELINE = 1000.0
PRESSURE_DELTA = {"press": 50.0, "sip": -50.0}
PRESSURE_NOISE = 0.05  # +/- uniform


def _pressure_value(mode):
    """Raw barometer value for a pressure mode (None|'press'|'sip'), with jitter."""
    target = PRESSURE_BASELINE + PRESSURE_DELTA.get(mode, 0.0)
    return target + random.uniform(-PRESSURE_NOISE, PRESSURE_NOISE)


def build_state(pressure_mode):
    """One frame carrying a raw pressure value. A real tongue press touches the
    pad, so a press also touches its centre (the FSM needs that touch for click
    and drag); otherwise the frame is NO_TOUCH. pressure_mode=None gives baseline
    pressure and no touch, which returns the FSM to rest."""
    if pressure_mode == "press":
        frame = touch_frame(*SECTOR_CENTER["CENTER"])
    else:
        frame = no_touch_frame()
    return set_pressure(frame, _pressure_value(pressure_mode))


GESTURES = ("sip", "press")  # in priority order, when both are held


class Injector:
    def __init__(self, sender, hz, pulse_s):
        self.sender = sender
        self.period = 1.0 / hz
        self.pulse_s = pulse_s
        self.pulse = None       # (gesture, perf_counter deadline) of the current pulse
        self.held = set()
        self.lock = threading.Lock()
        self.running = True
        self.last_pressure = None

    def on_message(self, msg):
        gesture, _, action = msg.partition(" ")
        with self.lock:
            if gesture not in GESTURES or action not in ("", "on", "off"):
                print(f"ignored datagram {msg!r}", file=sys.stderr)
            elif action == "":
                self.pulse = (gesture, time.perf_counter() + self.pulse_s)
            elif action == "on":
                self.held.add(gesture)
            else:
                self.held.discard(gesture)

    def _pressure(self):
        # A held gesture wins over a pulse: holding is the longer, deliberate act.
        with self.lock:
            for gesture in GESTURES:
                if gesture in self.held:
                    return gesture
            if self.pulse and time.perf_counter() < self.pulse[1]:
                return self.pulse[0]
            return None

    def run(self):
        next_t = time.perf_counter()
        while self.running:
            pressure = self._pressure()
            # Stream while active, and send one baseline frame on the way out.
            if pressure is not None or self.last_pressure is not None:
                self._send(build_state(pressure))
            if pressure != self.last_pressure:
                print(pressure or "release")
            self.last_pressure = pressure
            next_t += self.period
            dt = next_t - time.perf_counter()
            if dt > 0:
                time.sleep(dt)
            else:
                next_t = time.perf_counter()

    def _send(self, frame):
        if self.sender is not None:
            self.sender.send([frame])


def listen(sock, inj):
    while inj.running:
        try:
            data, _ = sock.recvfrom(64)
        except OSError:
            return
        inj.on_message(data.decode("ascii", "replace").strip().lower())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=None, help="side-band serial port (auto-detected if a single side-band port is present)")
    ap.add_argument("--udp-port", type=int, default=UDP_PORT, help="localhost UDP port the Talon script sends to (must match user.mouthpad_bridge_port)")
    ap.add_argument("--hz", type=float, default=50.0, help="frame rate while a press or sip is active")
    ap.add_argument("--pulse-ms", "--press-ms", type=float, default=150.0, help="how long a pop holds its sip")
    ap.add_argument("--dry-run", action="store_true", help="log noises without opening the device")
    args = ap.parse_args()

    sender = None
    if not args.dry_run:
        try:
            sender = GestureSender(port=args.port)
        except RuntimeError as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            return 2
        print(f"\nUSB: {sender.port}")
    else:
        print("\ndry run: no device")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("127.0.0.1", args.udp_port))
    except OSError as e:
        print(f"ERROR: can't listen on udp 127.0.0.1:{args.udp_port}: {e}", file=sys.stderr)
        if sender is not None:
            sender.close()
        return 2
    print(f"listening for Talon on udp 127.0.0.1:{args.udp_port}")
    print(f"pop = sip ({args.pulse_ms:g} ms) | hiss = press (held) | Ctrl-C = quit\n")

    inj = Injector(sender, args.hz, args.pulse_ms / 1000.0)
    threading.Thread(target=listen, args=(sock, inj), daemon=True).start()
    try:
        inj.run()
    except KeyboardInterrupt:
        pass
    finally:
        inj.running = False
        sock.close()
        if sender is not None:
            sender.close()
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
