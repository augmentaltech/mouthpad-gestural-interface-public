# Talon Voice → MouthPad bridge

Drives a MouthPad's sip and press from [Talon Voice](https://talonvoice.com)'s
two built-in noises, so someone who can make a mouth sound can exercise MouthPad
gesture profiles without a MouthPad in their mouth. Talon recognises these noises
out of the box, with no training and no speech model:

| Talon noise | MouthPad |
|---|---|
| pop (lip pop) | sip, held for `--pulse-ms` (default 150 ms) |
| hiss (sustained "ssss") | tongue press with a touch at the pad centre, for as long as the hiss lasts |

A pop is a single event, so the bridge turns it into a short sip pulse. A hiss
has a start and an end, so it maps directly onto a held press. If both overlap,
the held press wins. The mapping lives in the Talon script; the bridge takes
either gesture as a pulse or a hold.

```
mic --Talon noise--> mouthpad_noise.py --UDP localhost--> talon_bridge.py --USB CDC side-band--> MouthPad hardware key
                     (inside Talon)                              |
                                                     mouthpad_gestural_interface
```

| File | Role |
|---|---|
| `talon-user/mouthpad_noise.py` | Talon user script: registers `pop` / `hiss` and forwards them as UDP datagrams |
| `talon-user/mouthpad_noise.talon` | Voice commands `mouthpad noise on` / `mouthpad noise off` |
| `talon_bridge.py` | The bridge: holds the device link and streams frames to it |

## Why two halves

Talon runs user scripts in its own embedded Python. Rather than installing
`pyserial` and this library into it, the Talon script uses only the standard
library and sends one-word UDP datagrams to `127.0.0.1:47700`. The bridge runs in
your normal Python, holds the device link, and can be tested without Talon.

| Datagram | Meaning |
|---|---|
| `sip` / `press` | pulse it for `--pulse-ms` |
| `sip on` / `press on` | hold it |
| `sip off` / `press off` | let go |

## What goes on the wire

A press also touches the centre of the pad, `(512, 384)`, as a real tongue press
does; without that touch, click and drag doesn't work. Otherwise touch is
NO_TOUCH, and the release frame lifts the touch. The raw barometer value is `1000.0` baseline, `+50` during a press, `-50` during a sip,
with ±0.05 of jitter. Frames stream at `--hz` while a press or sip is active, and
one baseline frame is sent when it ends to return the FSM to rest.

## Run

```sh
pip install ../..                                   # the mouthpad-gestural-interface library
ln -sfn "$PWD/talon-user" ~/.talon/user/mouthpad    # load the Talon half (Talon hot-reloads)
python talon_bridge.py                              # auto-detect the port
python talon_bridge.py --pulse-ms 250 --hz 50       # longer sip pulse
python talon_bridge.py --dry-run                    # just log noises, no device
python talon_bridge.py --port /dev/tty.usbmodem1234
```

Test the bridge without Talon by sending datagrams yourself:

```sh
echo -n sip | nc -u -w0 127.0.0.1 47700
echo -n "press on" | nc -u -w0 127.0.0.1 47700; sleep 1; echo -n "press off" | nc -u -w0 127.0.0.1 47700
```

## Notes

- **Conflicting bindings**: the Talon community config binds pop to a mouse click
  and hiss to scrolling in some modes (`user.mouse_enable_pop_click`,
  `user.mouse_enable_hiss_scroll`). Turn those off, or the noise will do both.
- Say `mouthpad noise off` to stop forwarding without unloading the script;
  switching off mid-hiss sends `press off` so the bridge doesn't stay pressing.
- Talon only reports a hiss after it has lasted a moment, so a press starts a
  beat late; pops have little latency.
- To use a different UDP port, pass `--udp-port` to the bridge and set
  `user.mouthpad_bridge_port` to match in a Talon `settings():` block.
- UDP is fire-and-forget: noises made while the bridge isn't running are dropped,
  and Talon logs nothing for them.
- Requires only the library; there is no `requirements.txt` of its own.
