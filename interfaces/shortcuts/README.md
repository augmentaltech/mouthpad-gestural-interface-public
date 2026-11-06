# Keyboard shortcuts from custom gestures

Number keys 1–6 send a MouthPad generic **custom gestures**, and a gesture profile
turns each one into an editing shortcut. The keys stand in for any input a third
party might wire up (a switch box, a foot pedal, a classifier): the script only
says *which button was tapped*, and the profile decides what that does.

| Key | Custom gesture (source / type / subtype) | macOS | Windows |
|---|---|---|---|
| 1 | `switchBox` / `tap` / `button1` | Copy ⌘C | Copy Ctrl+C |
| 2 | `switchBox` / `tap` / `button2` | Paste ⌘V | Paste Ctrl+V |
| 3 | `switchBox` / `tap` / `button3` | Cut ⌘X | Cut Ctrl+X |
| 4 | `switchBox` / `tap` / `button4` | Undo ⌘Z | Undo Ctrl+Z |
| 5 | `switchBox` / `tap` / `button5` | Redo ⇧⌘Z | Redo Ctrl+Y |
| 6 | `switchBox` / `tap` / `button6` | Select all ⌘A | Select all Ctrl+A |

```
keys 1-6 --> shortcut_keys.py --custom gesture--> MouthPad FSM --HID shortcut--> focused app
                  |                               (the profile's
       mouthpad_gestural_interface                 transitions)
```

| File | Role |
|---|---|
| `shortcut_keys.py` | Sends one custom-gesture frame per key press |
| `MacOS-custom-gesture-shortcuts.mkprofile` / `Windows-custom-gesture-shortcuts.mkprofile` | Name the gestures in `customGestures` and map each to a shortcut |
| `test_shortcut_keys.py` | Tests the key → gesture → shortcut mapping against both profiles |
| `requirements.txt` | `pynput`; the library itself installs from the repo root |

## How the names become indices

The device matches gestures by number. The profile's `customGestures` table gives
the names their numbers (`switchBox` = source 10, `tap` = type 1, `buttonN` =
subtype N), and the script reads the same table, so the two can't drift apart.
Rebinding a key to another shortcut is a profile edit; the script doesn't change.

## Run

1. Load `MacOS-custom-gesture-shortcuts` (or the Windows one) in the companion
   app, not the app's built-in `MacOS-Shortcuts` radial menu.
2. Plug in a MouthPad hardware key over USB.
3. Run:

   ```sh
   pip install ../..                  # the mouthpad-gestural-interface library
   pip install -r requirements.txt    # pynput, for global key capture
   python shortcut_keys.py            # --dry-run to try the key handling without a device
   ```

4. Focus any text field and press 1–6.

The script holds the number keys back from the focused app on macOS and Windows,
so only the shortcut arrives. On Linux the digit still types as well. macOS asks
for Accessibility (or Input Monitoring) permission for the terminal the first time.

## Requires firmware support

The device has to emit an injected custom gesture and match it against the
profile's custom triggers. Firmware without custom-gesture support drops the
`custom_gesture_*` fields, so the keys do nothing.
