# Robodoz3r

A cheerful autonomous construction worker for LEGO MINDSTORMS EV3, using the
[shared EV3 MicroPython setup](../README.md#shared-ev3-setup).

## What it does

- Raises its blade in greeting, chirps, and sets off to work.
- Shows faces and job announcements on the brick's screen.
- Backs away from obstacles with reversing beeps, then turns to find a new route.
- Makes longer escape turns when the way remains blocked.
- Takes a dance break after every 12–20 seconds of work: the 48-count
  **Floor Demolition** routine, with Boot Up, Bulldozer Shuffle, Gear Shift,
  Hydraulic Wave, Demolition Mode, and System Shutdown sections.
- Adapts the routine's human gestures to track pulses, turns, freezes, and blade
  lifts. Each count lasts 600 milliseconds; the full dance lasts about 29 seconds
  before it returns to work with the blade lowered.
- Checks for obstacles during its dance and before resuming forward movement.

## Wiring and setup

The program assumes these ports. Adjust [`config.py`](config.py) if yours differ.

| Part | Port |
| --- | --- |
| Left track motor | `C` |
| Right track motor | `B` |
| Blade motor | `A` |
| Infrared sensor, facing forward | `S4` |

This autonomous program does not use the remote or touch sensor.

1. Complete the [shared setup and device connection](../README.md#shared-ev3-setup).
2. Before each start, gently position the blade just above the floor, with room
   to lift. This position becomes zero; there is no automatic homing against a
   mechanical stop.
3. On the first run, support the chassis with the tracks clear of the floor.
   Check that the salute lifts the blade and both tracks drive forward after
   the greeting. Stop if either direction is wrong. In `config.py`, change the
   corresponding `*_DIRECTION` to the opposite direction. Directions and blade travel must be verified
   on your build; they have not been tested on physical hardware here.
4. Place it on a clear, level floor. Select **Robodoz3r: Download and Run** in
   VS Code's Run and Debug menu, then press `F5`. The entry point is
   [`main.py`](main.py).
5. Release the launch button, then press the brick's **center button** again to
   finish, or use its normal program-stop
   control. The program brakes all three motors when it exits or raises an error.

To dance once without cruising, change the Robodoz3r configuration's `program`
in [`.vscode/launch.json`](../.vscode/launch.json) to end in
`Robodoz3r/dance.py`, then press `F5`. Use the same wiring and starting blade
position. The standalone dance brakes all motors when it finishes, detects an
obstacle, or receives a new center-button press. `main.py` continues to import
the same routine for its periodic dance breaks.

Keep it away from edges and stairs: the forward infrared sensor cannot detect
drop-offs or obstacles behind it. The program does not detect jammed motors.

## Tuning

[`config.py`](config.py) contains speeds, obstacle distance, blade lift, and dance
timings. Speeds and blade angles refer to the **motor shaft**, not the blade itself.
The infrared threshold uses proximity units from 0–100, not centimeters.
It defaults to 55 to react earlier with the sensor behind the blade. Increase
`OBSTACLE_DISTANCE` if it still gets too close to walls; verify clearance on your build.

Start with the small 60-degree blade salute. Each blade gesture is braked after 600 milliseconds without checking for jams.
Check its starting position, direction, and clearance before increasing travel. Keep fingers away
from the tracks and blade linkage during operation.

Motor gestures use the [Pybricks EV3 motor API](https://pybricks.com/ev3-micropython/ev3devices.html).
Short tones and screen expressions use the [EV3 Brick API](https://pybricks.com/ev3-micropython/hubs.html).
No additional packages or sound assets are needed.

## Test without a robot

From the repository root:

```bash
cd Robodoz3r
python3 -m unittest discover -s tests -v
```

Tests simulate motors, sensors, and the brick. They cover greetings, obstacle
avoidance, repeated escapes, dancing, operation with jammed motors, wiring, and
shutdown on button presses or failures. Physical movement still needs testing
on the robot.
