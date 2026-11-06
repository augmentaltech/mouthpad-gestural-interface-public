#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.
"""Keyboard -> custom gestures -> keyboard shortcuts, through a MouthPad.

Each number key 1-6 sends the device one generic custom gesture: a "tap" from
"button1".."button6" of a "switchBox" source. Those names are not built into the
device. The gesture profile's customGestures table gives them indices, and its
transitions map each tap to a shortcut:

  1 copy   2 paste   3 cut   4 undo   5 redo   6 select all

The device sends the shortcut over its own HID link, so it lands in whichever
app has focus. The number keys themselves are held back from that app on macOS
and Windows; on Linux they still type.

The key-to-gesture map lives here and the gesture-to-shortcut map lives in the
profile, so swapping the profile rebinds the keys without touching this script.
Load the same profile in the companion app first.

Usage:  python shortcut_keys.py [--profile MacOS-custom-gesture-shortcuts.mkprofile] [--port COMx] [--dry-run]
"""
import argparse
import json
import os
import sys
import threading

from mouthpad_gestural_interface import GestureSender, custom_gesture_frame

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILE = os.path.join(
    HERE, "Windows-custom-gesture-shortcuts.mkprofile" if sys.platform == "win32" else "MacOS-custom-gesture-shortcuts.mkprofile")

# Key -> (source, type, subtype) names in the profile's customGestures.
KEY_GESTURES = {str(n): ("switchBox", "tap", f"button{n}") for n in range(1, 7)}

# macOS virtual keycodes of the number-row keys, for holding them back.
MAC_KEYCODES = {"1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22}
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105


def resolve_gestures(profile):
    """Key -> (source, type, subtype) indices from the profile's customGestures."""
    tables = profile.get("customGestures", {})
    resolved = {}
    for key, names in KEY_GESTURES.items():
        indices = []
        for table, name in zip(("sources", "types", "subtypes"), names):
            if name not in tables.get(table, {}):
                raise ValueError(f"profile's customGestures.{table} has no '{name}'")
            indices.append(tables[table][name])
        resolved[key] = tuple(indices)
    return resolved


def shortcut_labels(profile):
    """Key -> the label of the transition its gesture triggers, for logging."""
    events = {
        (e.get("source"), e.get("gestureType"), e.get("gestureSubtype")): name
        for name, e in profile.get("events", {}).items()
    }
    labels = {}
    for state in profile.get("states", {}).values():
        for t in state.get("transitions", []):
            for key, names in KEY_GESTURES.items():
                if events.get(names) in t.get("triggerEvents", []) and "label" in t:
                    labels.setdefault(key, t["label"])
    return labels


class ShortcutKeys:
    """Sends one gesture frame per key press; auto-repeat while held sends nothing."""

    def __init__(self, sender, gestures, labels):
        self.sender = sender
        self.gestures = gestures
        self.labels = labels
        self.held = set()
        self.lock = threading.Lock()

    def key_down(self, key):
        if key not in self.gestures:
            return
        with self.lock:
            if key in self.held:
                return
            self.held.add(key)
        print(f"{key} -> {self.labels.get(key, '?')}")
        if self.sender is not None:
            self.sender.send([custom_gesture_frame(*self.gestures[key])])

    def key_up(self, key):
        with self.lock:
            self.held.discard(key)


def make_listener(keyboard, keys):
    """A pynput keyboard listener that feeds ``keys`` and, on macOS and Windows,
    holds the mapped keys back from the focused app."""
    char_callbacks = {
        "on_press": lambda k: keys.key_down(getattr(k, "char", None)),
        "on_release": lambda k: keys.key_up(getattr(k, "char", None)),
    }

    if sys.platform == "darwin":
        suppressed = {MAC_KEYCODES[k] for k in keys.gestures}

        def darwin_intercept(event_type, event):
            import Quartz
            code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            return None if code in suppressed else event

        return keyboard.Listener(darwin_intercept=darwin_intercept, **char_callbacks)

    if sys.platform == "win32":
        # A suppressed event never reaches on_press, so the filter handles it.
        def win32_event_filter(msg, data):
            key = chr(data.vkCode) if 0x31 <= data.vkCode <= 0x39 else None
            if key not in keys.gestures:
                return True
            if msg in (WM_KEYDOWN, WM_SYSKEYDOWN):
                keys.key_down(key)
            elif msg in (WM_KEYUP, WM_SYSKEYUP):
                keys.key_up(key)
            listener.suppress_event()

        listener = keyboard.Listener(win32_event_filter=win32_event_filter)
        return listener

    return keyboard.Listener(**char_callbacks)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default=DEFAULT_PROFILE, help="the .mkprofile loaded on the device")
    ap.add_argument("--port", default=None, help="side-band serial port (auto-detected if a single side-band port is present)")
    ap.add_argument("--dry-run", action="store_true", help="log key presses without opening the device")
    args = ap.parse_args()

    try:
        from pynput import keyboard
    except ImportError:
        print("ERROR: pynput not installed. Run: pip install -r requirements.txt", file=sys.stderr)
        return 2

    with open(args.profile) as f:
        profile = json.load(f)
    try:
        gestures = resolve_gestures(profile)
    except ValueError as e:
        print(f"ERROR: {args.profile}: {e}", file=sys.stderr)
        return 2

    sender = None
    if not args.dry_run:
        try:
            sender = GestureSender(port=args.port)
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2

    keys = ShortcutKeys(sender, gestures, shortcut_labels(profile))
    listener = make_listener(keyboard, keys)

    print(f"profile {os.path.basename(args.profile)}: "
          + "  ".join(f"{k} {keys.labels.get(k, '?')}" for k in sorted(gestures)))
    print("Ctrl-C to quit\n")
    listener.start()
    try:
        listener.join()
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        if sender is not None:
            sender.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
