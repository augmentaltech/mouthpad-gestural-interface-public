# Wrist → MouthPad (camera)

Drives a MouthPad's cursor from wrist movement seen by a webcam, through the
[MediaPipe hand landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker).
Two examples, one per cursor model:

| Example | Wrist pose becomes | Profile mode | Cursor |
|---|---|---|---|
| `wrist_touch.py` | a synthetic **tongue touch** | tongue control | **velocity**: bend further to go faster, neutral to stop |
| `wrist_imu.py` | a synthetic **IMU rotation** | head control | **position**: the cursor follows the hand |

Both use the same two axes:

| Wrist movement | Axis | Touch | Rotation |
|---|---|---|---|
| Wave toward your right / left (abduction / adduction) | horizontal | east / west of centre | cursor right / left |
| Bend back / forward (extension / flexion) | vertical | north / south of centre | cursor up / down |

```
camera --MediaPipe--> wrist_pose.py --(side, lift)--> wrist_touch.py / wrist_imu.py --USB CDC side-band--> MouthPad
                                                                  |
                                                       mouthpad_gestural_interface
```

| File | Role |
|---|---|
| `wrist_pose.py` | Camera + hand landmarker, the wrist angles, the shared run loop and preview |
| `wrist_touch.py` | Wrist angles → touch point |
| `wrist_imu.py` | Change in wrist angles → orientation delta |
| `test_wrist.py` | Tests the angle maths and both mappings, with no camera |
| `requirements.txt` | `mediapipe`, `opencv-python`; the library itself installs from the repo root |

## Measuring the wrist

MediaPipe reports 21 hand landmarks but no wrist joint angle, and the forearm is
mostly out of frame. So the hand's direction stands in for it: the **mean
direction of the four fingers' proximal phalanges** (knuckle to middle joint),
in MediaPipe's metric world coordinates. A wave to the side turns that
direction within the image plane, and bending the wrist tilts it toward or
away from the camera.

Both angles are measured against a neutral pose captured when tracking starts,
so hold your hand still, palm toward the camera, for the first half second.
Press `c` in the preview window to recapture it, `q` to quit. Keep the forearm
still: moving it moves the hand direction too.

Curling the fingers also turns the proximal phalanges, so keep them loosely
straight.

## Touch: `wrist_touch.py`

The angles place a touch in the raw 1024×768 touch frame, the way a tongue held
off-centre does; the firmware runs its real gesture and cursor pipeline on it.
Each axis has its own full-reach range: `--side-range` degrees of wave (default
30) and `--lift-range` degrees of measured lift (default 10). Lift is narrower
because MediaPipe barely resolves fingers tilting toward or away from the
camera: that shows up mostly as a small change in estimated depth, so a full
wrist bend reads as only a few degrees. Watch the `lift` readout in the preview
at a full bend and set `--lift-range` to about that. Within `--deadband` of
neutral (default 0.2, a fraction of each axis's reach, so it is equally wide on
both), or with no hand in view, the frame is NO_TOUCH and the cursor stops. Every frame also carries a baseline
pressure reading so the profile sees neutral pressure.

## Rotation: `wrist_imu.py`

Each camera frame, the change in the two angles since the last frame (times
`--gain`, default 1) becomes a small rotation sent as the IMU orientation delta.
The head mouse moves the cursor by about 30 px per degree of rotation, so the
cursor tracks the hand and stays put when it's still.

The frame also carries the head-movement gesture: the firmware derives it from
the real IMU before the injected orientation delta replaces the real one, so
without it the profile's cursor-move transition would never fire. Each frame
also has no touch and baseline pressure.

The firmware maps rotation axes to cursor axes according to how the device is
lying, read from the real IMU's gravity. `--axes` picks the mapping to target:
`seated` (the default), `capsule-up` or `capsule-down`. If the cursor's axes
come out swapped or reversed, try another.

## Run

```sh
pip install ../..                   # the mouthpad-gestural-interface library
pip install -r requirements.txt     # mediapipe and OpenCV
python wrist_touch.py               # tongue-control mode: wrist sets cursor velocity
python wrist_imu.py                 # head-control mode: wrist sets cursor position
```

The first run downloads the hand model (`hand_landmarker.task`, ~8 MB) next to
the scripts. macOS asks for camera permission for your terminal.

Common options: `--dry-run` to track without a device, `--no-preview` to skip
the window, `--camera N` for another camera, `--mirror` to swap left and right,
`--port` to name the side-band port.
