# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

"""Unit tests for the reduced gesture proto and frame builders.

The load-bearing invariant is wire compatibility with the device's canonical
proto: a serialized MouthwareMessage must carry the gesture command at field 28
so the device's full parser routes it into its message_body oneof as
developer_test_io_command. That is asserted directly on the wire bytes here, so
the check needs neither the device nor the canonical bindings.
"""
from mouthpad_gestural_interface import (
    custom_gesture_frame,
    frame_bytes,
    no_touch_frame,
    play_gesture_vector,
    pressure_frame,
    quaternion_frame,
    sector_frame,
    touch_frame,
)
from mouthpad_gestural_interface._pb import Gestures_pb2 as G
from mouthpad_gestural_interface._pb import MouthwareMessage_pb2 as MM


def test_top_level_tag_is_field_28():
    # developer_test_io_command is field 28, wire type 2 (length-delimited):
    # tag = 28 << 3 | 2 = 226, varint-encoded as 0xE2 0x01.
    raw = play_gesture_vector([touch_frame(500, 690)]).SerializeToString()
    assert raw[:2] == b"\xe2\x01"


def test_touch_frame_round_trips():
    msg = play_gesture_vector([touch_frame(160, 360)])
    got = MM.MouthwareMessage.FromString(msg.SerializeToString())
    frame = got.developer_test_io_command.play_gesture_vector.frames[0]
    assert frame.HasField("touch_point")
    assert (frame.touch_point.x, frame.touch_point.y) == (160, 360)
    assert not frame.HasField("pressure")


def test_sector_frame_matches_center():
    frame = sector_frame("N")
    assert (frame.touch_point.x, frame.touch_point.y) == (500, 690)


def test_pressure_and_quaternion_overrides_round_trip():
    msg = play_gesture_vector([pressure_frame(1050.0), quaternion_frame(1, 0, 0, 0)])
    got = MM.MouthwareMessage.FromString(msg.SerializeToString())
    frames = got.developer_test_io_command.play_gesture_vector.frames
    assert abs(frames[0].pressure - 1050.0) < 1e-4
    assert frames[0].HasField("pressure")
    assert frames[1].HasField("q_delta")
    assert frames[1].q_delta.w == 1.0


def test_no_touch_frame_carries_touchpad_gesture():
    frame = no_touch_frame()
    assert len(frame.gestures) == 1
    g = frame.gestures[0]
    assert g.source == G.GS_TOUCHPAD
    assert g.touchpad_gesture_type == G.TGT_NO_TOUCH


def test_custom_gesture_uses_the_canonical_field_numbers():
    # duration = field 8, custom_gesture_source = 12, custom_gesture_type = 13,
    # custom_gesture_subtype = 14, all varints: tags 0x40, 0x60, 0x68, 0x70.
    g = custom_gesture_frame(10, 1, 3).gestures[0]
    assert g.SerializeToString() == bytes([0x40, 1, 0x60, 10, 0x68, 1, 0x70, 3])
    assert g.source == G.GS_UNSPECIFIED


def test_custom_gesture_omits_an_unset_type_and_subtype():
    g = custom_gesture_frame(12).gestures[0]
    assert g.WhichOneof("gesture_type") is None
    assert g.WhichOneof("gesture_subtype") is None
    assert g.custom_gesture_source == 12


def test_custom_gesture_type_zero_is_still_sent():
    g = custom_gesture_frame(10, 0, 0).gestures[0]
    assert g.WhichOneof("gesture_type") == "custom_gesture_type"
    assert g.WhichOneof("gesture_subtype") == "custom_gesture_subtype"


def test_custom_region_locations_follow_the_compass_sectors():
    assert G.TL_CUSTOM_0 == 10
    assert G.TL_CUSTOM_49 == 59


def test_empty_vector_cancels_playback():
    # An empty frame list is a valid "cancel playback" command.
    got = MM.MouthwareMessage.FromString(play_gesture_vector([]).SerializeToString())
    assert len(got.developer_test_io_command.play_gesture_vector.frames) == 0


def test_frame_bytes_has_a_two_byte_little_endian_length_prefix():
    msg = play_gesture_vector([touch_frame(1, 2)])
    payload_len = len(msg.SerializeToString())

    framed = frame_bytes(msg)
    assert framed[0] == (payload_len & 0xFF) and framed[1] == (payload_len >> 8)
    assert len(framed) == payload_len + 2


def test_frame_bytes_handles_a_payload_longer_than_one_byte_can_count():
    big = play_gesture_vector([touch_frame(1, 1) for _ in range(300)])
    payload_len = len(big.SerializeToString())
    assert payload_len > 255
    framed = frame_bytes(big)
    assert int.from_bytes(framed[:2], "little") == payload_len
