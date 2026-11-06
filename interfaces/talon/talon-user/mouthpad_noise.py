# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

"""Forward Talon's pop and hiss noises to talon_bridge.py.

Runs inside Talon. Symlink this folder into ~/.talon/user (see the README); the
bridge, running outside Talon, turns the datagrams into MouthPad sip and press.

  pop   -> "sip"                    (Talon reports a pop as a single event: a pulse)
  hiss  -> "press on" / "press off" (Talon reports hiss start and end: a hold)

Only the standard library is used, so nothing needs installing into Talon's
Python. UDP is fire-and-forget: if the bridge isn't running the noises are lost.
"""
import socket

from talon import Module, noise, settings

mod = Module()
mod.setting(
    "mouthpad_bridge_port",
    type=int,
    default=47700,
    desc="localhost UDP port talon_bridge.py listens on",
)

_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_enabled = True
_hissing = False


def _send(msg):
    try:
        _sock.sendto(msg.encode("ascii"), ("127.0.0.1", settings.get("user.mouthpad_bridge_port")))
    except OSError as e:
        print(f"mouthpad: send {msg!r} failed: {e}")


def on_pop(active):
    if _enabled:
        _send("sip")


def on_hiss(active):
    global _hissing
    if not _enabled:
        return
    _hissing = active
    _send("press on" if active else "press off")


@mod.action_class
class Actions:
    def mouthpad_noise_enable(enabled: bool):
        """Turn forwarding of pop/hiss to the MouthPad bridge on or off"""
        global _enabled, _hissing
        if not enabled and _hissing:
            # Don't leave the bridge pressing if we're switched off mid-hiss.
            _send("press off")
            _hissing = False
        _enabled = enabled
        print(f"mouthpad: noise forwarding {'on' if enabled else 'off'}")


noise.register("pop", on_pop)
noise.register("hiss", on_hiss)
