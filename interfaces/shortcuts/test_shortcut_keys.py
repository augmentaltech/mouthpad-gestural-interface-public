# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

import json
import os

import pytest

from shortcut_keys import HERE, ShortcutKeys, resolve_gestures, shortcut_labels

PROFILES = ["MacOS-custom-gesture-shortcuts.mkprofile", "Windows-custom-gesture-shortcuts.mkprofile"]


def load(name):
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)


class RecordingSender:
    def __init__(self):
        self.sent = []

    def send(self, frames):
        self.sent.append(frames)


@pytest.mark.parametrize("name", PROFILES)
def test_each_key_resolves_to_a_tap_of_its_button(name):
    gestures = resolve_gestures(load(name))
    assert gestures == {str(n): (10, 1, n) for n in range(1, 7)}


@pytest.mark.parametrize("name", PROFILES)
def test_each_key_triggers_its_shortcut(name):
    assert shortcut_labels(load(name)) == {
        "1": "Copy", "2": "Paste", "3": "Cut", "4": "Undo", "5": "Redo", "6": "Select all",
    }


def test_a_profile_missing_a_gesture_name_is_rejected():
    profile = load(PROFILES[0])
    del profile["customGestures"]["subtypes"]["button4"]
    with pytest.raises(ValueError, match="button4"):
        resolve_gestures(profile)


def test_a_press_sends_one_custom_gesture_and_auto_repeat_sends_nothing():
    sender = RecordingSender()
    keys = ShortcutKeys(sender, resolve_gestures(load(PROFILES[0])), {})
    keys.key_down("2")
    keys.key_down("2")
    keys.key_up("2")
    keys.key_down("2")

    assert len(sender.sent) == 2
    (frame,) = sender.sent[0]
    (g,) = frame.gestures
    assert (g.custom_gesture_source, g.custom_gesture_type, g.custom_gesture_subtype) == (10, 1, 2)


def test_unmapped_keys_send_nothing():
    sender = RecordingSender()
    keys = ShortcutKeys(sender, resolve_gestures(load(PROFILES[0])), {})
    keys.key_down("7")
    keys.key_down(None)
    assert sender.sent == []
