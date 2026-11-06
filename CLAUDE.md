# Designing MouthPad gesture profiles (`.mkprofile`)

Reference for writing `.mkprofile` gesture profiles for the MouthPad. The gestures
this repo injects (touch, press, sip, head movement) are the inputs these profiles
map to actions, so the gestural conventions below also say what an interface here
should send. Check every profile against the validation rules below before
presenting it.

## What is a .mkprofile?

A JSON file that maps MouthPad gestures (touchpad touches, sips, puffs, head movement) to keyboard/mouse actions. The device is a mouth-operated input device — the user interacts via a tongue touchpad, breath pressure (sip/puff), and head IMU.

---

## Schema

### Top-level structure
```json
{
  "version": 1,                           // optional
  "profileName": "string",
  "profileType": "radial" | "menu" | "game",
  "events": { "<eventName>": EventData },
  "states": { "<stateName>": StateData },
  "headControlModes": ["stateName", ...],
  "tongueControlModes": ["stateName", ...],
  "customRegions": [ CustomRegionData ],  // optional
  "customGestures": CustomGestures        // optional
}
```

- `profileType`: `"radial"` for radial/menu profiles (`"menu"` is an accepted alias), `"game"` for
  direct input mapping. Only `"game"` is treated specially — the app classifies any other value
  (including a missing field) as a radial/menu profile. The bundled radial profiles use `"radial"`.
- `headControlModes`: states available when controlling with head movement
- `tongueControlModes`: states available when controlling with tongue/touchpad only
- `customRegions`: optional list of up to 50 custom rectangular touchpad regions (coordinates 0–255)
- `version`: optional spec version, an integer of at least 1. A profile without one is version 0.
  It exists so future parsers can branch on the spec a profile was written against.
- `customGestures`: optional names for gesture sources, types and subtypes the proto enums
  don't name, so events can trigger on firmware gestures by index. See CustomGestures below.

### EventData
```json
{
  "source": ".gsBarometer" | ".gsTouchpad" | ".gsIMU",

  // Barometer (sip/puff):
  "barometerGestureType": ".bgtPress" | ".bgtSip" | ".bgtNeutral",
  "barometerGestureSubtype": ".bgsShort" | ".bgsLong" | ".bgsUnspecified",

  // Touchpad:
  "touchpadGestureType": ".tgtTouchTriangle" | ".tgtTouchTriangleEnd" | ".tgtSwipe" | ".tgtNoTouch" | ".tgtTouchCustomRectangle" | ".tgtTouchCustomRectangleEnd",
  "touchpadLocation": ".tlNorth" | ".tlNortheast" | ".tlEast" | ".tlSoutheast" | ".tlSouth" | ".tlSouthwest" | ".tlWest" | ".tlNorthwest" | ".tlDeadzone" | ".tlUnspecified" | ".tlCustom0" ... ".tlCustom39",
  "minGestureDurationCycles": 10,   // optional; default -1 (no minimum)
  "maxGestureDurationCycles": 20,   // optional; default Int32 max (2147483647)
  // Cycles run at 20 Hz (~50ms each). Use these for hold detection or ignoring brief touches.

  // IMU:
  "imuGestureType": ".igtHeadMovement" | ".igtHeadTilt" | ".igtTap",
  "imuGestureSubtype": ".igsUnspecified" | ".igsImuTiltUp" | ".igsImuTapSingle" // etc.
}
```

A name with a leading `.` (`.gsImu`, `.igtTap`, `.tlNorth`) is a lookup of a built-in proto
enum value. A gesture the proto enums don't name is a **custom gesture**: its `source` is a
`customGestures` name written without the dot, and it uses `gestureType` / `gestureSubtype`
in place of the per-sensor fields above:
```json
{
  "source": "gsHeadSwitch",   // a customGestures.sources name: no leading dot
  "gestureType": "hgtTap",    // optional; a customGestures.types name
  "gestureSubtype": "hgsLeft" // optional; a customGestures.subtypes name
}
```

**Note:** Many common events are built-in (no need to define them in `events`). See Built-in Events below.

### StateData
```json
{
  "repr": "string or emoji",         // display label; wrap SF Symbol name in parens: "(cursorarrow)"
  "transitions": [ TransitionData ],
  "regions": [0, 1, ...],            // optional: indices into customRegions
  "pointerFeedback": "...",          // optional
  "stateTransitionMatchingType": ".stmtSequential" | ".stmtAllMatching",  // optional
  "hideTouch": false,                // optional: hide the touchpad sectors UI for this state
  "showPressureBar": false           // optional: surface the sip/puff pressure bar for this state
}
```

**Visual feedback flags** (`hideTouch`, `showPressureBar`) are state-level UI hints consumed by the companion app — they do not affect firmware behavior. Use them on states where the touchpad sectors are irrelevant (e.g. a dictation/listening state where input is voice-driven) or where pressure feedback is the salient signal.

**`stateTransitionMatchingType` values:**
- `.stmtSequential` (default): evaluates transitions in order, executes only the first matching one ("first match wins").
- `.stmtAllMatching`: evaluates all transitions and executes every one that matches. Use in game states where multiple independent gestures (e.g. head movement for aiming AND a held touchpad direction for movement) must fire simultaneously each cycle.

### TransitionData
```json
{
  "triggerEvents": ["eventName", ...],   // empty [] = default/fallback transition
  "nextStateIndex": "stateName" | ".leftClick" | ".rightClick" | ".neutral" | ".move" | ".multiStepActionReturn" | "b_Dictation",  // omit to stay in this state
  "mouseKeyboardActions": [ ActionData ],  // max 5 actions
  "appActions": [ { "appAction": ".aaXxx" } ],  // requires .atTriggerAppTransitionActions
  "label": "string",   // optional display label
  "repr": "string"     // optional per-transition repr
}
```

- **Default transition**: `triggerEvents: []` — must be the **last** transition in the list.
- **Transition ordering**: more-specific triggers before less-specific. A transition with fewer trigger events must not appear after one with more — it would shadow the later one.
- **Swipe before touch**: if both a swipe and a touch event exist at the same location, the swipe transition must appear **before** the touch transition.

### Built-in States (use as nextStateIndex)
- `.leftClick` — perform a left click
- `.rightClick` — perform a right click
- `.neutral` — idle/neutral state
- `.move` — cursor movement state
- `.multiStepActionReturn` — return to the state saved by `.atSetMultiStepActionReturn`

### App-generated states (use as nextStateIndex without defining them)
The companion app builds these states itself each time it loads a profile, so a profile
targets one by name without defining it in `states`. Their names take no leading `.`. More
may be added; the validator's error for an undefined state lists the current ones.

- `b_Dictation` — dictation with the dictation tool the user selected in the app's settings
  (Augmental's own transcription, or a third-party dictation app).
  - The transition that enters it starts dictation. The app **replaces that transition's
    `mouseKeyboardActions` and `appActions`** with the tool's start step, and labels it
    "Dictation" unless it has a `label`; its `triggerEvents` and `repr` are kept.
  - Inside it, **press** transcribes and **sip** cancels; both return to the state it was
    entered from. The touchpad view is hidden and the pressure bar shown.
  - The app adds one copy per state that enters it, named `b_Dictation__<state>`, each with
    2 transitions that count toward the transition limit.
  - With no dictation tool selected, its transitions only return.

  Prefer it over wiring `.aaStartMicrophoneRecording` / `.aaTranscribeAudioInput` /
  `.aaCancelAudioInput` by hand, since it follows the user's choice of tool. A profile that
  defines its own state named `b_Dictation` uses that definition, and nothing is generated.

### ActionData (mouseKeyboardActions)
```json
{ "actionType": ".atXxx", ...params }
```

**Mouse actions:**
- `.atLeftButtonPress` / `.atLeftButtonRelease` / `.atLeftButtonToggle`
- `.atRightButtonPress` / `.atRightButtonRelease` / `.atRightButtonToggle`
- `.atMiddleButtonPress` / `.atMiddleButtonRelease` / `.atMiddleButtonToggle`
- `.atScrollUp` / `.atScrollDown` / `.atScrollLeft` / `.atScrollRight`
- `.atCursorMove` — move cursor (used with IMU/head; params: `xCursorMovement`, `yCursorMovement`)
- `.atCursorStop` — stop cursor movement
- `.atVirtualMouseMove` — virtual mouse movement

**Keyboard actions:**
```json
{
  "actionType": ".atKeystrokes",
  "keycodes": [".keyA", ".keyEnter", ...],       // max 6 keycodes
  "modifierKeys": [".keyModLshift", ".keyModLcmd", ".keyModLctrl", ".keyModLalt"],
  "keystrokeType": ".keystrokePressAndRelease" | ".keystrokeHold" | ".keystrokeToggleModifiers",
  "repeatEveryNCycles": 0,   // optional; 0 = fire once on trigger (default)
  "holdModifiers": false     // optional; if true, releases regular keys but keeps modifiers held (e.g. Cmd+Tab navigation)
}
```

**Media actions:**
- `.atMediaPlayPause`, `.atMediaVolumeUp`, `.atMediaVolumeDown`

**State/flow actions:**
- `.atTriggerAppTransitionActions` — required alongside any `appActions`
- `.atSetMultiStepActionReturn` — saves current state as return point for multi-step
- `.atResetMultiStepActionReturnToNeutral` — clears the saved multi-step return, resetting to neutral
- `.atSetMode` — changes the neutral state persistently (e.g. from a radial menu selection); use this to switch between tongue/head control modes without requiring the user to pick a mode in the app
- `.atClearKeystrokes` — release all held keys
- `.atClearMouse` — release all held mouse buttons

**Forbidden action types** (cannot be used in profiles):
- `.atPause`, `.atResetPressure`, `.atResume`, `.atRecalibrate`, `.atMouseAndKeyCombo`

### App Actions (appActions array)
Require `.atTriggerAppTransitionActions` in the same transition's `mouseKeyboardActions`. No limit on number of app actions per transition (unlike `mouseKeyboardActions` which is capped at 5).

```
.aaShowRadialMenu / .aaHideRadialMenu / .aaToggleRadialMenu / .aaRadialMenuSelect
.aaShowOnScreenKeyboard / .aaHideOnScreenKeyboard
.aaSetOnScreenKeyboardShortcuts
.aaCycleOnScreenKeyboardKeyset
.aaSelectKey
.aaMoveMouseToRightEdgeOfWindow / .aaMoveMouseToBottomEdgeOfWindow
.aaMoveMouseToBottomRightCornerOfWindow / .aaMoveMouseToTopLeftCornerOfWindow
.aaMoveMouseToScreenTopLeftCorner / .aaMoveMouseToScreenTopRightCorner
.aaMoveMouseToScreenBottomLeftCorner / .aaMoveMouseToScreenBottomRightCorner
.aaMoveMouseToScreenCenter
.aaMoveMouseToScreenTopEdge / .aaMoveMouseToScreenBottomEdge
.aaMoveMouseToScreenLeftEdge / .aaMoveMouseToScreenRightEdge
.aaMoveMouseToNextScreenCenter
.aaStartMicrophoneRecording
.aaShowDictationWindow / .aaHideDictationWindow
.aaCursorSensitivitySlow / .aaCursorSensitivityNormal / .aaCursorSensitivityFast
.aaCancelAudioInput / .aaTranscribeAudioInput / .aaVoiceCommandLookup / .aaClearVoiceCommandState
.aaCorrectTrainingGesture / .aaIncorrectTrainingGesture
.aaShowShortcutsBrowser / .aaHideShortcutsBrowser
.aaShortcutsBrowserNextGroup / .aaShortcutsBrowserPrevGroup
.aaShortcutsBrowserScrollUp / .aaShortcutsBrowserScrollDown / .aaShortcutsBrowserSelect
```

**Parameterized (plugin) app actions** — host-executed; the action object carries
per-instance parameters as sibling fields of `appAction` (validated by type):

- `.aaMouthpadMessageOutput` — write a string to the custom "mouthpad message
  output" BLE service. The app silently connects in the background (no
  pairing/bonding) to any device advertising the service and writes there.
  ```json
  { "appAction": ".aaMouthpadMessageOutput", "message": "hello" }
  ```
  Required: `message` (non-empty string).
- `.aaUartWrite` — write a string to a serial/UART port.
  ```json
  { "appAction": ".aaUartWrite", "port": "COM3", "message": "hi", "baud": 115200 }
  ```
  Required: `port`, `message` (non-empty strings). Optional: `baud` (positive
  integer, default 115200).
- `.aaUdpWrite` — send a string over UDP to a port on **localhost** (127.0.0.1).
  ```json
  { "appAction": ".aaUdpWrite", "port": 9000, "message": "hi" }
  ```
  Required: `port` (integer 1-65535), `message` (non-empty string). Localhost
  only — no `ip`/`host` field is accepted (a stray one is a validation error).
- `.aaLaunchApp` — launch an application. **Importing** a profile that contains
  this prompts the user for consent (it runs a program on their machine).
  ```json
  { "appAction": ".aaLaunchApp", "macos": "com.apple.Terminal", "windows": "C:/Windows/System32/notepad.exe", "args": ["..."] }
  ```
  Required: at least one of `macos` / `windows` (non-empty string). macOS value
  is a bundle id, app name, or `.app` path (launched via `open`); Windows value
  is an `.exe` path (or any shell-openable target). Optional: `args` (array of
  strings, passed as discrete argv — never shell-interpolated).

### Built-in Events (no need to define in `events`)
These are always available in any state's `triggerEvents`:

**Pressure:**
`press_event_start`, `press_continued`, `sip_event_start`, `sip_continued`,
`neutral_pressure_event`, `long_press_event`, `long_sip_event`

**Touchpad (all 10 locations × multiple gesture types):**
For each location in `north northeast east southeast south southwest west northwest deadzone unspecified`:
- `touch_<loc>` — finger down in zone
- `touch_<loc>_end` — finger lifted after touch
- `touch_<loc>_any_len` — touch of any duration
- `hold_<loc>` — sustained touch
- `swipe_<loc>` — swipe in direction
- `swipe_<loc>_start` — start of swipe
- `swipe_<loc>_end` — end of swipe
- `swipe_<loc>_end_any_len`
- `swipe_and_hold_<loc>`

**Other:**
`swipe_init`, `imu_move_event`, `no_touch_event`, `touch_event_anywhere`, `touch_deadzone`

### CustomRegionData
```json
{ "xmin": 10, "ymin": 20, "xmax": 100, "ymax": 200 }
```
- Max 50 custom regions per profile.
- Referenced in states via `"regions": [0, 1, ...]` (indices into `customRegions`).
- Use event touchpadLocation `.tlCustom0`, `.tlCustom1`, etc. and gesture types `.tgtTouchCustomRectangle` / `.tgtTouchCustomRectangleEnd`.

### CustomGestures
```json
"customGestures": {
  "sources":  { "gsHeadSwitch": 10 },
  "types":    { "hgtTap": 7 },
  "subtypes": { "hgsLeft": 2 }
}
```
Each table maps a name to the index the firmware matches on. These names are not proto
lookups, so they never take a leading `.`: a name that starts with one is rejected here, and
an event that writes `.gsHeadSwitch` or `.hgtTap` asks for a built-in proto value and fails as
unknown. An event triggers on a custom gesture like this:
```json
"head_switch_left": {
  "source": "gsHeadSwitch",
  "gestureType": "hgtTap",
  "gestureSubtype": "hgsLeft"
}
```
- **Sources**: indices must be at least 10 and must not be a built-in `GestureSource` value.
  Source names share the `source` field with the built-ins, so they can't reuse one (`gsImu`).
- **Types**: indices 0–255. **Subtypes**: indices 0–127. These are the sizes the firmware stores.
- `gestureType` and `gestureSubtype` are optional; one left out matches any type or subtype
  from that source.
- They go only with a custom source, and a custom source takes only them: none of the
  per-sensor fields (`imuGestureType`, `touchpadLocation`, …).
- The app sends a custom gesture in the trigger's dedicated `custom_gesture_source`,
  `custom_gesture_type` and `custom_gesture_subtype` proto fields.
- A trigger only fires if the firmware emits that (source, type, subtype). Naming an index
  does not create a gesture on the device, and firmware without custom-gesture support
  never matches one.

---

## Validation Rules (enforced by validator)

1. **No missing events**: every event name in `triggerEvents` must be defined in `events` or be a built-in event name.
2. **Default transition last**: a transition with `triggerEvents: []` must be the last in its state.
3. **Max 5 actions** per transition.
4. **App actions need trigger**: any `appActions` require `.atTriggerAppTransitionActions` in the same transition's `mouseKeyboardActions`.
5. **Swipe before touch**: at the same touchpad location, swipe transitions must appear before touch transitions.
6. **No transition shadowing**: a transition with fewer trigger events must not follow one with more at the same location (less-specific first).
7. **Max 6 keycodes** per `.atKeystrokes` action.
8. **No forbidden action types**: `.atPause`, `.atResetPressure`, `.atResume`, `.atRecalibrate`, `.atMouseAndKeyCombo`.
9. **Valid keystrokeType**: must be `.keystrokePressAndRelease`, `.keystrokeHold`, or `.keystrokeToggleModifiers` if specified.
10. **Valid app action strings**: must be one of the known `.aa*` values listed above.
11. **Max 50 custom regions**; `xmin <= xmax` and `ymin <= ymax`.
12. **Known gesture names**: every event's `source`, type and subtype must be a built-in proto name or, for a custom gesture, one defined in `customGestures`.
13. **Custom gestures are separate**: `gestureType` / `gestureSubtype` only with a custom source, which takes no per-sensor fields; `customGestures` names have no leading `.`.
14. **Custom gesture indices in range**: sources at least 10, not built-in and not a built-in name; types 0–255; subtypes 0–127.
15. **Version**: `version`, if present, is at least 1.
16. **Defined states**: every `nextStateIndex` names a state in `states` (with or without a leading `.`), a built-in state or an app-generated state; every `headControlModes` / `tongueControlModes` entry names a state in `states`.

## Menu-select sound convention (not validator-enforced)

A menu transition that fires a **one-shot** keystroke (`.keystrokePressAndRelease`, or no
`keystrokeType` at all, which defaults to it) carries the select sound:

```json
"mouseKeyboardActions": [ { "actionType": ".atTriggerAppTransitionActions" }, ... ],
"appActions": [ { "appAction": ".aaRadialMenuSelect" } ]
```

A **held** key (`.keystrokeHold`) must not — it re-fires every device frame, so the sound
would machine-gun. Clicks are excluded too: they already sound through the mouse-click path.

Hand-written profiles should follow this. The companion app's profile editor maintains it
automatically on save, in both directions, so a sector retargeted between tap and hold gains
or loses the sound without the author doing anything.

---

## Design Guidelines

- **Always check** a profile against the validation rules above before presenting it.
- **Firmware transition limit**: profiles are capped at **120 total transitions** across all states, including those of app-generated states. Keep profiles lean; prefer reusing states over duplicating transitions.
- **Use `.atSetMode` sparingly**: while profiles support dynamic mode changes via `.atSetMode`, prefer not to use it. Mode changes triggered from within a profile can be surprising and hard to reason about. Only use `.atSetMode` when there is no reasonable alternative.
- **Barometer trigger events**: prefer `sip_event_start` and `press_event_start` as trigger events for barometer-driven transitions. These fire on the leading edge of the gesture, giving a clean, immediate response. Avoid `sip_continued` / `press_continued` for one-shot actions — those fire every cycle while the gesture is held, which is only appropriate for repeating actions (e.g. scroll, cursor move).
- **Gestural language — press vs sip**: these have distinct semantic roles that should be respected across all profiles:
  - **Press** = *accept / confirm / execute*. Use for left click, Enter, accepting dictation, confirming a selection. Press is the "yes" gesture.
  - **Sip** = *open / back / cancel*. Use for opening menus (radial menu, right-click context menu), backtracking (going up a level in a menu hierarchy), or cancellation (the final step of backtracking — metaphorically "undoing" the current context). Sip is the "navigate" gesture.
  - Avoid inverting these roles without strong justification. Consistency across profiles reduces cognitive load for the user.
  - Touch gestures: typically good to enforce a minimum gesture time of ~10 cycles to avoid false positives. Using the "_end" variant is good for robust selections. Whenever possible, try to take advantage of natural spatial mappings for shortcuts: up/down/left/right, WASD, cmd+tab & cmd+shift+tab, cmd+1` & cmd+shift+` and others have a nice spatial mapping. 
  - **Touch location accessibility**: a full tongue press on the trackpad tends to land in the center deadzone, making it the one location reliably hit without vision — prefer it for cancellation-type actions or actions with neutral consequences. Ranked easiest to hardest to land on:
    1. `deadzone`
    2. `north`
    3. `east` / `west`
    4. `northeast` / `northwest`
    5. `south`
    6. `southeast` / `southwest`

    (a slash indicates equal accessibility). This ranking is **empirical** — drawn from observed tongue dexterity across 100+ users. It is not derived from tactile landmarks on the board, and does not follow from the tongue's north/south range of motion; do not re-derive the order from first principles. Two patterns fall out of it worth internalizing:
    - **Every northern sector beats its southern mirror** (`north` > `south`, `northeast`/`northwest` > `southeast`/`southwest`). This is pure dexterity.
    - **Cardinals beat diagonals.** Partly dexterity, partly geometry: `east`/`west` cover more surface area than the `northeast`/`northwest` diagonals, so they are simply bigger targets to land on. The same geometry holds for `south` over `southeast`/`southwest`, but it changes nothing there — `south` already ranks below `east`/`west` on dexterity alone.

    Put frequent or high-stakes actions in the easiest sectors, and reserve `southeast`/`southwest` for rare or low-consequence ones.
- **Cursor movement (ratchet polarity)**: head-control states gate `.atCursorMove` against the touchpad. Two patterns are supported — pick one per profile and apply it consistently across head-control states.

  **Regular ratchet (default — touch is the brake).** Cursor moves freely with head movement; touching the pad anywhere stops it. Best for users who want continuous head-driven cursor control with an explicit "stop" gesture.
  ```jsonc
  {
    "triggerEvents": ["touch_event_anywhere"],
    "mouseKeyboardActions": [ { "actionType": ".atCursorStop" } ]
  },
  {
    "triggerEvents": ["imu_move_event"],
    "mouseKeyboardActions": [ { "actionType": ".atCursorMove" } ]
  }
  ```
  **Inverted ratchet (touch is the gas).** Cursor only moves while the tongue is on the deadzone; lifting (or moving off the deadzone) stops it. Useful for users who want positive intent before any cursor motion, or for combining head-cursor with tongue shortcuts in non-deadzone sectors.
  ```jsonc
  {
    "triggerEvents": ["imu_move_event", "touch_deadzone"],
    "mouseKeyboardActions": [ { "actionType": ".atCursorMove" } ]
  },
  {
    "triggerEvents": [],
    "mouseKeyboardActions": [ { "actionType": ".atCursorStop" } ]
  }
  ```
- **Radial menu pattern**: use an intermediate init state (e.g. `radialMenuInit`) to distinguish a quick sip (abort) from a held sip (open menu).
- **Persistent radial menu (cursor-move during menu)**: if the `radialMenu` state includes the regular ratchet (`touch_event_anywhere` → `.atCursorStop`, `imu_move_event` → `.atCursorMove`) so the user can keep moving the cursor while the menu is open, sector actions should fire their keystrokes/clicks **without** transitioning back to `mouse` and **without** `.aaHideRadialMenu` — the menu stays up so the user can chain actions. The only transitions that close the menu are **right click** (sip) and the explicit **return** sector. Plain `.atKeystrokes` actions in this style don't need `.atTriggerAppTransitionActions` since there are no app actions to trigger.
- **Swallow quarantine**: after certain cancelled gestures, route through a `swallow_quarantine` state that only exits on `neutral_pressure_event` + `no_touch_event`. This prevents accidental triggers.
- **`repr`**: keep labels short — they appear in the companion UI. Emojis are fine.
- **`label`**: use human-readable labels on transitions that the user sees (e.g. radial menu item names).
- **Modifier key toggling**: use `.keystrokeToggleModifiers` for sticky/latch-style modifier keys (hold Shift, Cmd, etc. until cleared with `.atClearKeystrokes`).
- **Multi-step actions**: use `.atSetMultiStepActionReturn` before `.atLeftButtonPress` so the device knows where to return after the click completes.
- **All trigger events must be satisfied simultaneously**: a transition fires only when every event in `triggerEvents` is active at the same time. This means listing mutually exclusive events (e.g. `touch_north` and `touch_south`, or two different pressure events) makes the transition unreachable — it can never fire. Do not combine touch events from different locations in a single `triggerEvents` array; the user only has one tongue contact point, so only one location can be active at once. To respond to any of several independent gestures, create separate transitions each with a single trigger event.
- **Game profiles**: use `profileType: "game"` and `stateTransitionMatchingType: ".stmtAllMatching"` in game states so that multiple simultaneous gestures (e.g. head-aim + directional movement) all fire each cycle.

---

## Profile fragments

Reusable pieces of a profile can be kept as fragment files:

- **`.fsmstate` files** — a single reusable `StateData` object. Can be copied into a profile's `states` map as-is. The profile constructor is responsible for adding transitions *into* and *out of* the state from surrounding states — the `.fsmstate` only defines what happens while inside the state.

- **`.transition` files** — a single `TransitionData` object. The `triggerEvents` field may be absent or empty and must be filled in by the profile constructor to suit the context; all other fields (`nextStateIndex`, `mouseKeyboardActions`, `appActions`, `label`, `repr`) are specified and should be used as-is.
