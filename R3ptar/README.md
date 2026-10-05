# 🐍 R3ptar: the robot snake with opinions

Give a LEGO® MINDSTORMS® EV3 R3ptar a little Python and a patch of floor, and it will slither off to investigate the world.

This project is for curious kids, playful grown-ups, LEGO fans, robot tinkerers, and anyone who thinks a hissing plastic snake should also know how to dance.

> **Warning:** may stare at furniture, bite suspicious objects, rattle dramatically, and throw an unexpected dance party.

## What can this snake do?

- Slither from side to side instead of driving like a boring box
- Look around with curious head turns and nods
- Spot nearby objects with its infrared sensor
- Hiss, open its mouth, strike, and back away
- Scan both sides before choosing an escape route
- Notice when its drive is stuck and try a stronger getaway
- Build a tiny map of obstacles and prefer places it has visited less
- Play a melody while wiggling its head and body

The map is deliberately small and simple: it is R3ptar's rough memory of the current adventure, not GPS. It disappears whenever the program restarts.

## Choose your adventure

| File | What happens |
| --- | --- |
| [`main.py`](main.py) | The full autonomous snake brain: exploring, mapping, biting, escaping, and getting unstuck |
| [`dance.py`](dance.py) | A musical head-and-body dance routine |
| [`basic.py`](basic.py) | A smaller, beginner-friendly autonomous program to read and remix first |
| [`config.py`](config.py) | Motor ports, speeds, timings, map size, and the dance melody |

## What you need

- A built LEGO MINDSTORMS EV3 **R3ptar**
- An EV3 Brick running EV3 MicroPython
- A microSD card and mini-USB cable for the EV3 setup
- Visual Studio Code with the **LEGO MINDSTORMS EV3 MicroPython** extension
- A clear patch of floor for snake business

New to EV3 MicroPython? Follow the official [Pybricks EV3 installation guide](https://pybricks.com/install/mindstorms-ev3/installation/) before continuing.

## Plug in the creature

The programs expect this wiring:

| Part | EV3 port |
| --- | --- |
| Infrared sensor | `S4` |
| Head-turn motor | `A` |
| Drive motor | `B` |
| Head-bend / bite motor | `D` |

Before starting a program, physically point R3ptar's head straight ahead and place the head-bend mechanism in its raised, resting position. The code calls that position zero.

## Wake the snake

1. Clone this repository and open the folder in Visual Studio Code.

   ```bash
   git clone https://github.com/YudakovAlex/fun_r3ptar.git
   cd fun_r3ptar
   ```

2. Turn on the EV3 Brick and connect it to your computer.
3. Make sure R3ptar is centered, resting, and sitting on the floor with room to move.
4. Press `F5` in Visual Studio Code to download and run `main.py`.

That is it. R3ptar should begin exploring on its own.

To run a different adventure, change `main.py` in [`.vscode/launch.json`](.vscode/launch.json) to `dance.py` or `basic.py`, then press `F5` again. The [Pybricks running-programs guide](https://pybricks.com/install/mindstorms-ev3/running-programs/) has more help with connecting, downloading, and launching EV3 code.

## Turn the personality knobs

Most values worth experimenting with live in [`config.py`](config.py):

```python
OBSTACLE_DISTANCE = 45       # When should R3ptar react?
MOVE_SPEED = 500             # How speedy is the slither?
HEAD_TURN_LIMIT = 50         # How far may the head turn?
MAP_SIZE = 17                # How big is the imaginary world?
DANCE_REPEATS = 2            # How long is the party?
```

You can also rewrite `MELODY` as pairs of `(frequency, duration)` values. Durations are in milliseconds.

Change one or two values at a time, test on the floor, and see what kind of creature appears. If the motors strain or the model moves too wildly, stop the program and choose gentler values.

## Peek inside the robot brain

The autonomous program uses a state machine, so each loop does a small piece of work instead of waiting through a whole reaction. Its basic decision trail looks like this:

```text
explore → detect obstacle → hiss and bite → back away
   ↑                                           ↓
   └─────── choose a less-blocked path ← scan left and right
```

While exploring, R3ptar estimates movement from the drive motor angle. It records visited cells and obstacles in a `17 × 17` grid, then scores possible directions. If the encoder says the snake is not making enough progress, it rattles, reverses, and searches for a new route.

There is plenty here to learn from: sensors, motors, sound, timing, random behavior, state machines, simple mapping, and safe motor shutdown.

## Test the brain without an EV3

The tests use pretend motors, sensors, and speakers, so they can run on a regular computer with Python 3:

```bash
python3 -m unittest discover -s tests -v
```

They check the important tricks: hardware ports, obstacle memory, path choices, stuck recovery, curious looks, slithering, dancing, and emergency braking.

## Play safely

- Start on the floor, away from stairs, table edges, pets, and fragile treasures.
- Keep fingers, hair, and loose clothing away from gears and the biting mechanism.
- Be ready to stop the program if a motor is straining.
- Younger builders should ask a grown-up for help preparing the microSD card and checking the wiring.

Now remix it, teach it a new tune, adjust its courage, or invent your own robot-animal behavior. Toys are more fun when you can open up the brain. 🤖✨

---

This is an unofficial fan project and is not sponsored or endorsed by the LEGO Group.
