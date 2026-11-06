# QuadStick → MouthPad

Lets a [QuadStick](https://quadstick.com) mouth-operated joystick stand in for a
MouthPad, so a QuadStick user can use MouthPad gesture profiles. The QuadStick's
joystick and sip/puff tubes become tongue touches, presses and sips on a MouthPad
hardware key, and the key runs whatever profile the MouthPad app has loaded.

| QuadStick | MouthPad |
|---|---|
| joystick position | tongue touch location |
| centre tube puff | tongue touch down (latches on) |
| centre tube sip | tongue touch up (latches off) |
| left tube puff | tongue press |
| left tube sip | sip |

The touch **latches**: a puff puts the tongue down and it stays down, following the
joystick, until a sip lifts it. Holding the puff is not required.

```
QuadStick --USB--> MouthPad app --USB--> MouthPad hardware key --> mouse, keyboard
```

## In the MouthPad app

The MouthPad app supports the QuadStick directly, as an experimental feature:

1. In the app's experiments, turn on **Emulate MouthPad^ with other assistive
   devices**. An **Other assistive devices** tab appears.
2. With the QuadStick plugged in, use **Load MouthPad^ emulation profile** in that
   tab. It writes `mouthpad.csv` (below) to the QuadStick. Then eject the
   QuadStick's drive, unplug it and reconnect it so it reads the new profile.
3. Turn on **Use QuadStick as MouthPad^**. The app forwards the QuadStick's input
   to the hardware key.

## The QuadStick profile

`mouthpad.csv` is the QuadStick-side profile this needs. It is a **pass-through**:
it maps every tube and the joystick to game-controller outputs and nothing to the
QuadStick's own mouse or keyboard outputs. That way the QuadStick only feeds the
MouthPad app and leaves the computer's cursor and keyboard alone; what each gesture
*does* is then up to the MouthPad profile.

The app installs it for you (above). To install it by hand, copy it onto the
QuadStick's USB drive as `default.csv`, which the QuadStick loads at boot:

```sh
cp "/Volumes/Quad Stick/default.csv" ~/quadstick-default-backup.csv   # keep your current profile
cp mouthpad.csv "/Volumes/Quad Stick/default.csv"
diskutil eject "/Volumes/Quad Stick"   # it won't re-read while the computer holds it
# unplug and reconnect the QuadStick
```

To go back, copy your backup over `default.csv` the same way.

`mouthpad.csv` leaves the side tube's hard sip unmapped, so the QuadStick's own
profile-switching (a long hard sip on the side tube) keeps working if you keep
several profiles on it.

The MouthPad's radial menus suit this input best when each sector selects after a
hold rather than when the touch lifts, since a latched touch doesn't lift on its
own.
