# MouthPad gestural interface

A MouthPad turns tongue touches, sips and presses, and head movement into mouse,
keyboard and app actions. What each gesture does is set by a **gesture profile**:
a JSON file (`.mkprofile`) that you can write yourself, and that an AI assistant
can write for you from a plain description of what you want.

This repo is for two things:

1. **Writing your own profiles**, by hand or with AI. [`CLAUDE.md`](CLAUDE.md) is
   the full profile specification, written so an AI assistant can follow it; this
   README gives the big picture.
2. **Driving profiles from your own sensors.** A MouthPad hardware key runs the
   MouthPad firmware without the mouthpiece, so a camera, switch, joystick or
   research device can stand in for the tongue, breath or head. The Python library
   and the examples here feed it.

## How a profile works

```
 gestures                     profile (a state machine)               actions
 ─────────                    ─────────────────────────               ───────
 tongue touch  ─┐        ┌─────────┐  sip held  ┌────────────┐        mouse moves and clicks
 sip / press   ─┼──────► │  mouse  │ ─────────► │ radial menu│ ─────► keystrokes and shortcuts
 head movement ─┤        └─────────┘ ◄───────── └────────────┘        media keys
 custom        ─┘           ▲  │       select          │              app actions:
                            └──┘                       │                • menus
                        press: click                   │                • on-screen keyboard
                                                       │                • dictation
                                                       │                • launching an app
                                                       ▼                • sending a message
                                                feedback in the MouthPad app:
                                                menu labels, touchpad view, pressure bar, sounds
```

**Gestures are the inputs.** Each comes from a source with a type and, optionally,
a subtype:

| Source | Gestures |
|---|---|
| Touchpad (tongue) | touch, hold, swipe and release in nine sectors (eight compass directions and the centre), or in up to 50 rectangular regions the profile defines |
| Barometer (breath) | press and sip, short or long, and neutral |
| IMU (head) | head movement, tilt, and taps |
| Custom | gestures a profile names itself, for sensors the built-in sources don't cover (see [Custom sensors](#custom-sensors-the-hardware-key)) |

A gesture can also be qualified by how long it lasts, which is how a profile tells
a quick sip from a held one.

**States and transitions are the logic.** A profile is a set of named states. Each
state lists transitions: *when these gestures happen, do these actions and move to
that state*. That makes modes and menus easy to express: a `mouse` state where the
tongue moves the cursor and a press clicks, a sip that opens a `radialMenu` state
where each touch direction is a different shortcut, a sip again to back out.

**Actions are the outputs**: cursor movement and clicks, scrolling, keystrokes
with modifiers (held, tapped or latched), media keys, and **app actions** run by
the MouthPad app, such as showing the radial menu or on-screen keyboard,
dictation, launching an application, or writing a message to a serial port, a
local UDP port or a Bluetooth service.

**Feedback is part of the profile too.** Each state and transition carries a short
label or icon, which the MouthPad app shows on the radial menu's sectors or the
touchpad view, so the user can see what each direction does. A state can show a
pressure bar while breath control matters, hide the touchpad when it doesn't, or
draw the profile's custom touch regions. Menu selections play a select sound.

**Two control modes.** A profile lists which states serve as the starting point
for tongue control (the tongue steers the cursor) and for head control (head
movement steers it), and the user switches between them in the app.

## Making a profile with AI

1. Open this repo in an AI coding assistant (Claude Code reads `CLAUDE.md`
   automatically; with other tools, point them at it).
2. Describe what you want in plain language, for example:
   - *"A profile for video editing: tongue moves the cursor, a quick sip opens a
     radial menu with play/pause, cut, undo, and jump back five seconds."*
   - *"Head control for drawing: press holds the mouse button, a long sip toggles
     to a menu of brush sizes."*
3. Ask it to check the result against the validation rules in `CLAUDE.md`.
4. Import the `.mkprofile` into the MouthPad app, which validates it again and
   loads it onto your MouthPad.

Profiles are readable, but tedious to edit by hand: a menu is a state with a
transition per sector, each carrying its gestures, actions and labels. We
recommend an AI coding assistant with `CLAUDE.md` as its context, even for small
changes. Trying a profile is safe: the app rejects an invalid profile before it
reaches the device, and loading a profile can't damage a MouthPad or a hardware
key. Load a different profile to undo it.

`CLAUDE.md` also carries the design conventions that make profiles comfortable to
use, so an assistant following it will apply them: press confirms and sip
navigates or backs out, frequent actions go in the touch sectors that are easiest
to reach, menus distinguish a quick sip from a held one, and so on.

## Custom sensors: the hardware key

Some uses want MouthPad profiles but different gestures: a camera tracking the
hand, a switch or foot pedal, a voice recognizer, a research sensor. The **MouthPad
hardware key** is a small USB device running the MouthPad firmware. It connects to
the MouthPad app like a MouthPad does, and takes its gestures from your program
over USB instead of from the mouthpiece. Everything else is unchanged: the app
loads profiles onto it, the profile turns gestures into actions, and the app shows
its menus and feedback.

```
your sensor ──► your program ──USB──► MouthPad hardware key ──► mouse, keyboard
                + this library        (runs the profile)
                                             ▲
                                             │ profiles, menus, feedback
                                        MouthPad app
```

**Why a hardware key, not just an app?** Device switching. Software that injects
mouse and keyboard events only controls the one computer it runs on. The hardware
key is a real Bluetooth device, like the MouthPad itself, and inherits the MouthPad's capabilities to switch between different bonded devices using the MouthPad app.

The hardware key is available to trusted second parties; email
[contact@augmental.tech](mailto:contact@augmental.tech) to get one.

Your program can send any mix of these each cycle:

| Send | It stands in for | A typical profile uses it for |
|---|---|---|
| a touch point (x, y) | where the tongue touches the pad | cursor velocity, menu selection |
| a pressure reading | breath | press to click, sip for menus |
| an orientation change | head movement | cursor position |
| a custom gesture | your own named gesture | whatever the profile maps it to |

The key only runs a profile while it is connected to the MouthPad app.

### Custom gestures or stand-in sensor readings?

The first three rows fake the MouthPad's own sensors: a touch point on the
1024×768 touchpad grid, a barometer pressure, and an orientation from motion
tracking. **For discrete gestures, don't fake sensors; send custom gestures.** A
switch, a pedal, a recognized hand pose or a voice command is a gesture of its own,
and naming it with a custom source, type and subtype keeps the profile readable
("pedal down → click") instead of pretending it was a sip. See
[`shortcuts`](interfaces/shortcuts).

There are two exceptions where stand-in readings are the right tool:

1. **Moving the pointer.** The firmware computes cursor motion on the device, and
   only from touch or orientation, in whichever of tongue or head control the user
   has selected in the app. To move the pointer, map your continuous output to
   either:
   - a **touch point**, with tongue control selected: distance from the centre
     sets the cursor's *velocity*, like a joystick;
   - an **orientation change**, with head control selected: rotation *displaces*
     the cursor, like a head mouse.

   The [`wrist`](interfaces/wrist) examples do both from a camera. Calling a hand
   pose a "tongue touch" is an abuse of terminology; if you have a strong use case
   for a cleaner pointer abstraction, tell us.
2. **An analogous sensor.** If your device does the same job as a MouthPad sensor,
   such as your own sip-and-puff tube or an extra-oral joystick moving the cursor,
   send its readings as that sensor and existing MouthPad profiles work unchanged.
   [`quadstick`](interfaces/quadstick) is an example.

Anything else, such as switch control, is usually best served by a custom gesture
set.

### Install

```sh
pip install .   # the library; each interface adds its own requirements.txt
```

### Library use

```python
from mouthpad_gestural_interface import (
    GestureSender, sector_frame, touch_frame, pressure_frame, quaternion_frame,
)

with GestureSender() as dev:            # finds the hardware key's USB port
    dev.send([sector_frame("N")])       # touch the North sector this cycle
    dev.send([touch_frame(300, 400)])   # or a raw 1024x768 touch point
    dev.send([pressure_frame(1050.0)])  # override barometer pressure
    dev.send([quaternion_frame(1, 0, 0, 0)])  # override IMU orientation delta
    dev.send([])                        # empty vector = release / cancel
```

A `GestureFrame` may combine overrides — build one and set several fields:

```python
from mouthpad_gestural_interface import touch_frame, set_pressure
f = set_pressure(touch_frame(500, 690), 1050.0)   # touch North *and* press
dev.send([f])
```

A gesture the built-in sources don't name is a custom gesture, sent by the indices a
profile's `customGestures` gives it (see [`shortcuts`](interfaces/shortcuts)):

```python
from mouthpad_gestural_interface import custom_gesture_frame
dev.send([custom_gesture_frame(source=10, gesture_type=1, gesture_subtype=2)])
```

Each `send([...])` is one device cycle (~30 Hz). Call it on your own clock to
stream motion; send `[]` to stop. For full control, build `MouthwareMessage`
objects with `mouthpad_gestural_interface.frames` and the raw modules under
`mouthpad_gestural_interface._pb`.

### Interfaces

`interfaces/` holds complete examples, each wiring a different input device to the
hardware key. Each has its own README with setup and details.

| Example | Input | Sent as | Shows |
|---|---|---|---|
| [`numpad`](interfaces/numpad) | keyboard numpad | touch sectors, press, sip | the smallest integration; a handy bench tool |
| [`talon`](interfaces/talon) | mouth noises via [Talon Voice](https://talonvoice.com) | sip (lip pop), press (hiss) | bridging another app's events into the key |
| [`wrist`](interfaces/wrist) | webcam hand tracking | touch point, or head rotation | the same sensor driving cursor velocity or cursor position |
| [`shortcuts`](interfaces/shortcuts) | number keys | custom gestures | naming your own gestures in a profile and mapping them to shortcuts |
| [`quadstick`](interfaces/quadstick) | [QuadStick](https://quadstick.com) mouth joystick | touch, press, sip | an existing assistive device, supported in the MouthPad app as an experimental feature; this folder has the QuadStick-side profile |

## Related Work

MouthPad profiles compared with other gesture-mapping systems, on these features:

1. **Text spec**: the profile is a JSON file.
2. **Profiles**: a user keeps several profiles, switches between them, and
   shares them.
3. **Stateful**: the file describes a state machine, not only a one-to-one
   mapping.
4. **Menu UI**: actions include on-screen UI, such as the radial menu, the
   on-screen keyboard and dictation, run by the companion app.
5. **UART, UDP, BLE**: actions include writing a message to a serial port, a
   localhost UDP port, or a BLE service.
6. **Any source**: gestures can come from other input devices, including
   research hardware on a serial port that isn't a standard HID device,
   through the hardware key.

| System | Text spec | Profiles | Stateful | Menu UI | UART | UDP | BLE | Any source |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **MouthPad** `.mkprofile` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [QuadStick](https://quadstick.s3.amazonaws.com/documents/user_manual/um/configuration.htm) | ✓ | ✓ | ◐ modes | ✗ | ✗ | ✗ | ✗ | ✗ |
| [LipSync](https://www.neilsquire.ca/the-lipsync-levels-up-the-new-lipsync-is-here/) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [Xbox Adaptive Controller](https://www.xbox.com/accessories-app) | ✗ | ✓ 3 | ◐ profiles, shift | ✗ | ✗ | ✗ | ✗ | ◐ switches |
| [Apple Switch Control](https://support.apple.com/en-us/119835) | ✗ | ✗ | ◐ recipes | ✓ | ✗ | ✗ | ✗ | ◐ switches, head, sounds |
| [Android Switch Access](https://support.google.com/accessibility/android/answer/11150722) | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ◐ switches, face |
| [Project Gameface](https://developers.googleblog.com/2023/06/project-gameface.html) | ✗ | ? | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [OptiKey](https://github.com/Optikey/Optikey/wiki) | ✓ | ◐ keyboard files | ◐ keyboard pages | ✓ | ✗ | ✗ | ✗ | ◐ gaze, mouse, switches |
| [AsTeRICS](https://www.asterics-foundation.org/?p=1067) | ✓ | ✓ | ? | ◐ | ? | ? | ? | ✓ |
| [Talon Voice](https://talonvoice.com/docs) | ✓ | ◐ | ✓ | ✓ | ◐ ¹ | ◐ ¹ | ◐ ¹ | ◐ ¹ |
| [Steam Input](https://partner.steamgames.com/doc/features/steam_controller/action_set_layers) | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ◐ gamepads |
| [BetterTouchTool](https://docs.folivora.ai/docs/actions/conditions/) | ◐ ² | ✓ | ✓ | ✓ | ◐ ¹ | ✓ OSC | ◐ ¹ | ◐ HID, MIDI |
| [Stream Deck](https://docs.elgato.com/sdk/plugins/manifest) | ◐ ² | ✓ | ◐ folders | ◐ on its keys | ◐ ³ | ◐ ³ | ◐ ³ | ✗ |
| [Logi Options+](https://futureisnow.logitech.com/en-us/software/logi-options-plus/actions-ring.html) | ✗ | ✓ | ✗ | ✓ | ◐ ³ | ◐ ³ | ◐ ³ | ✗ |
| [Karabiner-Elements](https://karabiner-elements.pqrs.org/docs/json/complex-modifications-manipulator-definition/to/set-variable/) | ✓ | ✓ | ✓ | ✗ | ◐ ¹ | ◐ ¹ | ◐ ¹ | ✗ |
| [Kanata](https://github.com/jtroo/kanata) | ✓ | ◐ config files | ✓ | ✗ | ◐ ¹ | ◐ ¹ | ◐ ¹ | ✗ |
| [AntiMicroX](https://github.com/AntiMicroX/antimicrox) | ✓ | ✓ | ◐ sets | ✗ | ◐ ¹ | ◐ ¹ | ◐ ¹ | ✗ |
| [QMK](https://docs.qmk.fm/feature_layers) / [ZMK](https://zmk.dev) | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [Unity Input System](https://docs.unity3d.com/Packages/com.unity.inputsystem@1.8/manual/ActionBindings.html) | ✓ | — ⁴ | ◐ | — ⁴ | — ⁴ | — ⁴ | — ⁴ | ◐ ⁵ |
| [Unreal Enhanced Input](https://dev.epicgames.com/documentation/en-us/unreal-engine/enhanced-input-in-unreal-engine) | ✗ | — ⁴ | ✓ | — ⁴ | — ⁴ | — ⁴ | — ⁴ | ◐ ⁵ |
| [OpenXR actions](https://openxr-tutorial.simul.co/linux/opengl/4-actions.html) | ✗ | — ⁴ | ◐ action sets | — ⁴ | — ⁴ | — ⁴ | — ⁴ | ◐ ⁵ |
| [libmapper](https://www.github.com/libmapper/libmapper) | ◐ ² | ◐ sessions | ✗ | ✗ | ✗ | ◐ OSC | ✗ | ✓ |
| [SCXML](https://www.w3.org/TR/scxml/) | ✓ | — ⁴ | ✓ | — ⁴ | — ⁴ | — ⁴ | — ⁴ | ✓ |

✓ built in; ◐ partly; ✗ no; — not applicable; ? not confirmed.

1. Only by running a script or shell command (Python in Talon).
2. Configured in a GUI; the saved configuration is a file.
3. Through third-party plugins.
4. A framework or format: the application supplies the actions.
5. Devices the engine or runtime supports, or ones added in code.

## Protocol

The library talks to the hardware key in the firmware's own protobuf format, with
no translation layer in between. It ships only the part of that format needed to
inject gestures, in [`src/proto`](src/proto):

| File | Contents |
|---|---|
| `MouthwareMessage.proto` | the message envelope, with only the gesture command |
| `GestureInject.proto` | `Quaternion`, `TouchPoint`, `GestureFrame`, `PlayGestureVector`, `DeveloperTestIOCommand` |
| `Gestures.proto` | `FSMGesture` and the gesture enums |
| `DeviceInfo.proto` | just enough of the device-info reply to tell devices apart |

Protobuf identifies fields by number, so this subset, which keeps the firmware's
field numbers, enum values and package name (`mouthware_message`), produces
exactly the bytes the firmware expects; the firmware ignores what it doesn't
receive.

### Wire framing

The hardware key is reached over its own USB port, which shows up as a serial
port (Nordic VID `0x1915`). Each serialized `MouthwareMessage` is sent with a
2-byte little-endian length prefix, at 115200 baud, 8N1, no flow control.
`GestureSender` finds the key's port by its VID; pass `port=` to choose one.

### Regenerating the bindings

The generated `src/mouthpad_gestural_interface/_pb/*_pb2.py` are checked in so the
package installs without a protobuf compiler. To regenerate after editing
`src/proto`:

```sh
pip install '.[dev]'   # grpcio-tools
make proto
```

## License

The message definitions, the profile specification, the library and the example
interfaces are licensed under the [PolyForm Noncommercial License
1.0.0](LICENSE): free for personal, research, educational and nonprofit use.
[`NOTICE`](NOTICE) adds two permissions on top:

- **With MouthPad hardware, any use is allowed**, commercial or not, including
  with the hardware key.
- **Profiles you write are yours** to use, share or sell, even when they are based
  on the examples or the specification.

Other commercial use, including a gesture-profile format, engine or tool based on
this repository, needs a commercial license: email [contact@augmental.tech](mailto:contact@augmental.tech).
