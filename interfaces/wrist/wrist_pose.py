# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Augmental Technologies, Inc.. See LICENSE and NOTICE.

"""Wrist orientation from a camera, via the MediaPipe hand landmarker.

MediaPipe has no wrist joint angle, and the forearm is mostly out of frame, so
the hand's direction stands in for it: the mean direction of the four fingers'
proximal phalanges (MCP -> PIP), in MediaPipe's metric "world" landmarks. With
the palm toward the camera and the forearm still, a wave to the side turns that
direction within the image plane (abduction / adduction, i.e. radial / ulnar
deviation), and bending the wrist tilts it toward or away from the camera
(flexion / extension). Both are measured against a neutral pose captured when
tracking starts, so only the change matters, not how the camera is mounted.

World landmarks share the image axes: x to the image's right, y down, z away
from the camera. The camera faces the user, so the user's right is the image's
left.
"""
import math
import os
import time
import urllib.request

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/latest/hand_landmarker.task")
DEFAULT_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

# (MCP, PIP) landmark indices of the index, middle, ring and little fingers.
PROXIMAL_PHALANGES = ((5, 6), (9, 10), (13, 14), (17, 18))


def finger_direction(points):
    """Unit mean direction of the four proximal phalanges; ``points`` is the 21
    hand landmarks as (x, y, z)."""
    sx = sy = sz = 0.0
    for mcp, pip in PROXIMAL_PHALANGES:
        dx, dy, dz = (points[pip][i] - points[mcp][i] for i in range(3))
        n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        sx, sy, sz = sx + dx / n, sy + dy / n, sz + dz / n
    n = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
    return sx / n, sy / n, sz / n


def direction_angles(direction):
    """(side, lift) in degrees for a finger direction.

    side: the in-plane angle, positive toward the user's right.
    lift: the out-of-plane angle, positive tilting away from the camera (wrist
    extension with the palm toward the camera).
    """
    x, y, z = direction
    side = math.degrees(math.atan2(-x, -y))
    lift = math.degrees(math.atan2(z, math.hypot(x, y)))
    return side, lift


class WristPose:
    """Smoothed (side, lift) angles relative to a neutral pose.

    The first ``calibration_frames`` frames with a hand in view set the neutral;
    until then, and whenever no hand is seen, ``update`` returns None.
    """

    def __init__(self, smoothing=0.5, calibration_frames=15, mirror=False):
        self.smoothing = smoothing
        self.calibration_frames = calibration_frames
        self.mirror = mirror
        self.recalibrate()

    def recalibrate(self):
        self._samples = []
        self._neutral = None
        self._smoothed = None

    def update(self, points):
        if points is None:
            self._smoothed = None
            return None
        side, lift = direction_angles(finger_direction(points))
        if self.mirror:
            side = -side
        if self._neutral is None:
            self._samples.append((side, lift))
            if len(self._samples) < self.calibration_frames:
                return None
            self._neutral = tuple(sum(s[i] for s in self._samples) / len(self._samples) for i in range(2))
        rel = (_wrap(side - self._neutral[0]), lift - self._neutral[1])
        if self._smoothed is None:
            self._smoothed = rel
        else:
            a = self.smoothing
            self._smoothed = tuple(a * p + (1 - a) * r for p, r in zip(self._smoothed, rel))
        return self._smoothed

    @property
    def calibrating(self):
        return self._neutral is None


def _wrap(deg):
    return (deg + 180.0) % 360.0 - 180.0


def ensure_model(path=DEFAULT_MODEL):
    if not os.path.exists(path):
        print(f"downloading the hand landmarker model to {path}")
        urllib.request.urlretrieve(MODEL_URL, path)
    return path


class HandCamera:
    """Camera frames with the landmarks of the first hand in each.

    ``frames()`` yields (bgr_image, world_points, image_points); the point lists
    are None when no hand is found.
    """

    def __init__(self, camera=0, model_path=DEFAULT_MODEL):
        import cv2
        import mediapipe as mp

        self._cv2 = cv2
        self._mp = mp
        vision = mp.tasks.vision
        options = vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=ensure_model(model_path)),
            running_mode=vision.RunningMode.VIDEO, num_hands=1)
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._capture = cv2.VideoCapture(camera)
        if not self._capture.isOpened():
            raise RuntimeError(f"could not open camera {camera}")
        self._t0 = time.monotonic()

    def frames(self):
        last_ms = -1
        while True:
            ok, bgr = self._capture.read()
            if not ok:
                return
            rgb = self._cv2.cvtColor(bgr, self._cv2.COLOR_BGR2RGB)
            image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
            # detect_for_video needs strictly increasing timestamps.
            ms = max(int((time.monotonic() - self._t0) * 1000), last_ms + 1)
            last_ms = ms
            result = self._landmarker.detect_for_video(image, ms)
            if result.hand_world_landmarks:
                world = [(p.x, p.y, p.z) for p in result.hand_world_landmarks[0]]
                pixels = [(p.x, p.y) for p in result.hand_landmarks[0]]
                yield bgr, world, pixels
            else:
                yield bgr, None, None

    def close(self):
        self._capture.release()
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def add_common_args(ap):
    ap.add_argument("--camera", type=int, default=0, help="camera index for OpenCV")
    ap.add_argument("--mirror", action="store_true", help="swap left and right, e.g. for a mirrored camera feed")
    ap.add_argument("--port", default=None, help="side-band serial port (auto-detected if a single side-band port is present)")
    ap.add_argument("--dry-run", action="store_true", help="track and print without opening the device")
    ap.add_argument("--no-preview", action="store_true", help="don't open the camera preview window")


def run(args, step):
    """Stream one frame per camera frame until quit.

    ``step(angles)`` gets the (side, lift) wrist angles, or None while
    calibrating or with no hand in view, and returns (gesture_frames, status).
    In the preview window, ``c`` recalibrates the neutral pose and ``q`` quits.
    """
    from mouthpad_gestural_interface import GestureSender

    sender = None
    if not args.dry_run:
        sender = GestureSender(port=args.port)
    pose = WristPose(mirror=args.mirror)
    print("hold the hand still, palm toward the camera, to set the neutral pose; c recalibrates, q quits")
    try:
        with HandCamera(args.camera) as camera:
            for bgr, world, pixels in camera.frames():
                angles = pose.update(world)
                frames, status = step(angles)
                if sender is not None:
                    sender.send(frames)
                if world is None:
                    status = "no hand"
                elif pose.calibrating:
                    status = "calibrating: hold still"
                if args.no_preview:
                    continue
                key = show_preview(bgr, pixels, [status])
                if key == "c":
                    pose.recalibrate()
                elif key in ("q", "\x1b"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if sender is not None:
            sender.close()


def show_preview(bgr, image_points, lines):
    """Draw the hand and status text, show the window, and return the key
    pressed (lower-case char) or None."""
    import cv2

    h, w = bgr.shape[:2]
    if image_points is not None:
        for mcp, pip in PROXIMAL_PHALANGES:
            a = (int(image_points[mcp][0] * w), int(image_points[mcp][1] * h))
            b = (int(image_points[pip][0] * w), int(image_points[pip][1] * h))
            cv2.line(bgr, a, b, (0, 200, 255), 3)
        wrist = (int(image_points[0][0] * w), int(image_points[0][1] * h))
        cv2.circle(bgr, wrist, 6, (0, 200, 255), -1)
    for i, line in enumerate(lines):
        cv2.putText(bgr, line, (12, 28 + 26 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 255, 40), 2)
    cv2.imshow("wrist", bgr)
    key = cv2.waitKey(1) & 0xFF
    return chr(key).lower() if key != 0xFF else None
