# Numpad → MouthPad bridge

Drives a MouthPad's firmware FSM from the keyboard's numpad, so anyone can
exercise MouthPad gesture profiles without a MouthPad in their mouth — the
smallest possible integration on top of `mouthpad_gestural_interface`, and a
handy bench tool for watching the FSM react.

| Numpad (NumLock on) | MouthPad |
|---|---|
| `7` `8` `9` | tongue touch NW / N / NE |
| `4`  `6` | tongue touch W / E |
| `1` `2` `3` | tongue touch SW / S / SE |
| `Enter` | tongue press |
| `+` | sip |

Keys are **held**, not latched: the touch lasts as long as the digit is down, and
releasing everything sends a NO_TOUCH + baseline-pressure frame that returns the
FSM to rest. The most recently pressed still-held digit wins, so rolling from `8`
to `9` moves the touch without a release in between.

```
keyboard --pynput--> numpad_bridge.py --USB CDC side-band--> MouthPad firmware
                            |
                   mouthpad_gestural_interface
```

| File | Role |
|---|---|
| `numpad_bridge.py` | The bridge |
| `requirements.txt` | `pynput`; the library itself installs from the repo root |

## What goes on the wire

Both channels are analog overrides — the firmware replaces its measured pressure
and estimated touch with these values and runs the real gesture + cursor
pipeline, so a held direction actually moves the cursor:

- **touch**: the sector's point in the raw 1024×768 touch frame, or NO_TOUCH.
- **pressure**: a raw barometer value — `1000.0` baseline, `+50` while `Enter`
  is held, `-50` while `+` is held, with ±0.05 of jitter so the value is never
  perfectly static.

## Key detection

A numpad key arrives as a plain digit char when NumLock is on, but some platforms
and layouts only report the virtual-key code, so the bridge accepts those too —
X11 `XK_KP_0..9` (65456–65465) and Windows/evdev `VK_NUMPAD0..9` (96–105), plus
`XK_KP_Add` / `VK_ADD` for `+`. Top-row digits work as well.

If the pad's north reads as the numpad's south, pass `--flip-ns` to swap the
vertical axis.

## Run

```sh
pip install ../..                   # the mouthpad-gestural-interface library
pip install -r requirements.txt     # pynput, for global key capture
python numpad_bridge.py             # auto-detect the port
python numpad_bridge.py --hz 50     # frame rate while a key is held (default 50)
python numpad_bridge.py --flip-ns   # swap north/south
python numpad_bridge.py --port /dev/tty.usbmodem1234
```

## Notes

- **macOS**: global key capture needs the terminal to hold Input Monitoring
  (System Settings → Privacy & Security → Input Monitoring). Without it pynput
  starts but never sees a key.
- Keystrokes still reach whatever window has focus — pynput observes, it does not
  swallow. Run it with a scratch window focused.
- The bridge sends one `PlayGestureVector` frame per cycle at `--hz`, and a
  release frame when the last key comes up.
