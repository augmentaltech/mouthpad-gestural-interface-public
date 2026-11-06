# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

import math

import pytest

from mouthpad_gestural_interface._pb import Gestures_pb2 as G
from wrist_imu import AXES, IDENTITY, Displacement, frame_for as imu_frame_for, q_delta_for
from wrist_pose import PROXIMAL_PHALANGES, WristPose, direction_angles, finger_direction
from wrist_touch import CENTER, frame_for as touch_frame_for, touch_point_for


def hand(side_deg=0.0, lift_deg=0.0, spread_deg=0.0):
    """21 landmarks whose proximal phalanges point ``side_deg`` toward the
    user's right (image left) and ``lift_deg`` away from the camera, each finger
    fanned ``spread_deg`` further than the last around that direction."""
    points = [(0.0, 0.0, 0.0)] * 21
    for i, (mcp, pip) in enumerate(PROXIMAL_PHALANGES):
        s = math.radians(side_deg + spread_deg * (i - 1.5))
        l = math.radians(lift_deg)
        base = (0.02 * i, 0.0, 0.0)
        d = (-math.sin(s) * math.cos(l), -math.cos(s) * math.cos(l), math.sin(l))
        points[mcp] = base
        points[pip] = tuple(b + 0.04 * c for b, c in zip(base, d))
    return points


def angles_of(points):
    return direction_angles(finger_direction(points))


def test_fingers_straight_up_read_as_neutral():
    side, lift = angles_of(hand())
    assert side == pytest.approx(0, abs=1e-6)
    assert lift == pytest.approx(0, abs=1e-6)


def test_a_wave_toward_the_users_right_is_positive_side():
    assert angles_of(hand(side_deg=20))[0] == pytest.approx(20)


def test_tilting_away_from_the_camera_is_positive_lift():
    side, lift = angles_of(hand(lift_deg=15))
    assert lift == pytest.approx(15)
    assert side == pytest.approx(0, abs=1e-6)


def test_the_direction_is_the_mean_of_the_four_fingers():
    assert angles_of(hand(side_deg=10, spread_deg=8))[0] == pytest.approx(10, abs=0.2)


def test_pose_reports_nothing_until_the_neutral_is_captured():
    pose = WristPose(smoothing=0, calibration_frames=3)
    assert pose.update(hand(side_deg=5)) is None
    assert pose.update(hand(side_deg=5)) is None
    assert pose.update(hand(side_deg=5)) == pytest.approx((0, 0), abs=1e-6)
    assert pose.update(hand(side_deg=17, lift_deg=-4)) == pytest.approx((12, -4))


def test_pose_reports_nothing_without_a_hand():
    pose = WristPose(smoothing=0, calibration_frames=1)
    pose.update(hand())
    assert pose.update(None) is None


def test_mirror_swaps_left_and_right():
    pose = WristPose(smoothing=0, calibration_frames=1, mirror=True)
    pose.update(hand())
    assert pose.update(hand(side_deg=10))[0] == pytest.approx(-10)


def test_recalibrate_takes_a_new_neutral():
    pose = WristPose(smoothing=0, calibration_frames=1)
    pose.update(hand())
    pose.recalibrate()
    pose.update(hand(side_deg=30))
    assert pose.update(hand(side_deg=30)) == pytest.approx((0, 0), abs=1e-6)


# --- touch -------------------------------------------------------------------

RANGES = dict(side_range=30, lift_range=10, deadband=0.2)


def test_a_neutral_wrist_lifts_the_touch():
    assert touch_point_for(3, -1, **RANGES) is None
    f, point = touch_frame_for((3, -1), 30, 10, 0.2)
    assert point is None
    assert f.gestures[0].touchpad_gesture_type == G.TGT_NO_TOUCH
    assert f.HasField("pressure")


def test_a_wave_right_touches_east_and_extension_touches_north():
    # The raw frame's x grows toward the user's left (West), y toward North.
    x, _ = touch_point_for(15, 0, **RANGES)
    _, y = touch_point_for(0, 5, **RANGES)
    assert x < CENTER[0]
    assert y > CENTER[1]


def test_bending_further_touches_further_out_up_to_the_edge():
    near = touch_point_for(10, 0, **RANGES)
    far = touch_point_for(30, 0, **RANGES)
    beyond = touch_point_for(90, 0, **RANGES)
    assert CENTER[0] > near[0] > far[0]
    assert beyond == far


def test_the_narrow_lift_range_amplifies_a_small_measured_lift():
    # A full wrist bend toward the camera reads as only a few degrees of lift.
    _, y = touch_point_for(0, 8, **RANGES)
    x, _ = touch_point_for(8, 0, **RANGES)
    assert y - CENTER[1] > CENTER[0] - x


def test_the_deadband_is_a_fraction_of_each_axis_reach():
    # 3 deg of lift is 30% of a 10 deg lift range: outside a 20% deadband, even
    # though 3 deg of side wave (10% of 30) is inside it.
    assert touch_point_for(0, 3, **RANGES) is not None
    assert touch_point_for(3, 0, **RANGES) is None


def test_no_hand_lifts_the_touch():
    f, point = touch_frame_for(None, 30, 10, 0.2)
    assert point is None
    assert f.gestures[0].touchpad_gesture_type == G.TGT_NO_TOUCH


# --- imu ---------------------------------------------------------------------

def fusion_pitch_yaw(q):
    """Pitch and yaw in degrees, decoded as the firmware's Fusion library does."""
    w, x, y, z = q
    pitch = math.degrees(math.asin(2 * (w * y - z * x)))
    yaw = math.degrees(math.atan2(w * z + x * y, 0.5 - y * y - z * z))
    return pitch, yaw


def firmware_cursor(q, axes):
    """The firmware head mouse's (x, y) cursor step for a q_delta, per orientation."""
    pitch, yaw = fusion_pitch_yaw(q)
    return {"seated": (pitch, -yaw), "capsule-up": (-yaw, -pitch), "capsule-down": (yaw, pitch)}[axes]


@pytest.mark.parametrize("axes", sorted(AXES))
def test_a_wave_right_moves_the_cursor_right(axes):
    x, y = firmware_cursor(q_delta_for(2.0, 0.0, axes), axes)
    assert x == pytest.approx(2.0, abs=1e-3)
    assert y == pytest.approx(0.0, abs=1e-3)


@pytest.mark.parametrize("axes", sorted(AXES))
def test_extension_moves_the_cursor_up(axes):
    # Screen y grows downward.
    x, y = firmware_cursor(q_delta_for(0.0, 3.0, axes), axes)
    assert x == pytest.approx(0.0, abs=1e-3)
    assert y == pytest.approx(-3.0, abs=1e-3)


def test_both_axes_at_once_decode_independently():
    x, y = firmware_cursor(q_delta_for(1.5, -2.5), "seated")
    assert (x, y) == (pytest.approx(1.5, abs=1e-2), pytest.approx(2.5, abs=1e-2))


def test_q_delta_is_a_unit_quaternion():
    assert sum(c * c for c in q_delta_for(7, -4)) == pytest.approx(1.0)


def test_displacement_is_the_change_since_the_last_frame_times_the_gain():
    d = Displacement(gain=2.0)
    assert d.step((10.0, 0.0)) == (0.0, 0.0)
    assert d.step((12.0, -1.0)) == pytest.approx((4.0, -2.0))
    assert d.step(None) == (0.0, 0.0)
    assert d.step((40.0, 5.0)) == (0.0, 0.0)


def test_a_still_wrist_sends_identity_and_no_head_movement():
    f = imu_frame_for(0.0, 0.0, "seated", 0)
    assert (f.q_delta.w, f.q_delta.x, f.q_delta.y, f.q_delta.z) == IDENTITY
    imu = [g for g in f.gestures if g.source == G.GS_IMU]
    assert [g.imu_gesture_type for g in imu] == [G.IGT_HEAD_NO_MOVEMENT]


def test_a_moving_wrist_sends_its_rotation_with_a_head_movement_gesture():
    # The firmware derives head movement from the real IMU before an injected
    # q_delta replaces it, so the frame has to carry the gesture itself.
    f = imu_frame_for(1.0, 0.5, "seated", 4)
    assert f.HasField("q_delta") and f.q_delta.w < 1.0
    imu = [g for g in f.gestures if g.source == G.GS_IMU]
    assert [g.imu_gesture_type for g in imu] == [G.IGT_HEAD_MOVEMENT]
    assert imu[0].gesture_duration_cycles == 4
    touch = [g for g in f.gestures if g.source == G.GS_TOUCHPAD]
    assert [g.touchpad_gesture_type for g in touch] == [G.TGT_NO_TOUCH]
