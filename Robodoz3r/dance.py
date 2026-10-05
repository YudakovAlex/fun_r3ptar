#!/usr/bin/env pybricks-micropython

"""The 48-count Floor Demolition routine for Robodoz3r."""

from pybricks.ev3devices import InfraredSensor, Motor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Button, Color, Stop
from pybricks.tools import StopWatch, wait

from config import (
    BLADE_DIRECTION, BLADE_LIFT_ANGLE, BLADE_PORT, DANCE_BEAT_TIME,
    INFRARED_SENSOR_PORT, LEFT_TRACK_DIRECTION, LEFT_TRACK_PORT,
    LOOP_DELAY, OBSTACLE_DISTANCE, RIGHT_TRACK_DIRECTION, RIGHT_TRACK_PORT,
    TURN_SPEED,
)


# Each count gives left/right track direction and an optional blade target.
# Pauses brake the tracks; blade angles stay within the existing salute travel.
DANCE_ROUTINE = (
    ("BOOT UP", (
        (0, 0, BLADE_LIFT_ANGLE // 2), (0, 0, BLADE_LIFT_ANGLE), (1, -1, None), (-1, 1, None),
        (0, 0, BLADE_LIFT_ANGLE // 2), (0, 0, BLADE_LIFT_ANGLE), (1, 1, None), (0, 0, None),
    )),
    ("BULLDOZER SHUFFLE", (
        (1, 1, None), (0, 0, None), (1, 1, None), (0, 0, None),
        (0, 0, BLADE_LIFT_ANGLE // 2), (0, 0, 0), (-1, -1, BLADE_LIFT_ANGLE // 2), (0, 0, 0),
    )),
    ("GEAR SHIFT", (
        (1, -1, BLADE_LIFT_ANGLE // 2), (0, 0, 0), (-1, 1, BLADE_LIFT_ANGLE // 2), (0, 0, 0),
        (1, -1, None), (1, -1, None), (0, 0, None), (-1, 1, None),
    )),
    ("HYDRAULIC WAVE", (
        (0, 0, BLADE_LIFT_ANGLE // 4), (0, 0, BLADE_LIFT_ANGLE // 2), (0, 0, BLADE_LIFT_ANGLE * 3 // 4), (0, 0, BLADE_LIFT_ANGLE),
        (0, 0, BLADE_LIFT_ANGLE // 2), (0, 0, 0), (1, 1, BLADE_LIFT_ANGLE // 2), (0, 0, BLADE_LIFT_ANGLE),
    )),
    ("DEMOLITION MODE", (
        (1, 1, None), (0, 0, None), (1, -1, BLADE_LIFT_ANGLE // 2), (-1, 1, 0),
        (-1, -1, None), (-1, -1, None), (0, 0, BLADE_LIFT_ANGLE), (0, 0, None),
    )),
    ("SYSTEM SHUTDOWN", (
        (1, -1, None), (1, -1, None), (-1, 1, None), (-1, 1, None),
        (0, 0, BLADE_LIFT_ANGLE // 2), (0, 0, 0), (0, 0, BLADE_LIFT_ANGLE // 2), (0, 0, 0),
    )),
)


def step(dozer, now):
    """Perform one count; the main loop handles timing and interruptions."""
    dozer._brake_tracks()
    section, counts = DANCE_ROUTINE[dozer.dance_beat // 8]
    left, right, blade_target = counts[dozer.dance_beat % 8]
    dozer._show(section, "^   ^", Color.GREEN)
    if blade_target is not None:
        dozer._blade_to(blade_target, now)
    dozer.brick.speaker.beep((523, 659, 784, 1047)[dozer.dance_beat % 4], 60)
    if left:
        dozer.left.run_time(left * TURN_SPEED, DANCE_BEAT_TIME, then=Stop.BRAKE, wait=False)
    if right:
        dozer.right.run_time(right * TURN_SPEED, DANCE_BEAT_TIME, then=Stop.BRAKE, wait=False)
    dozer.deadline = now + DANCE_BEAT_TIME


def main():
    """Dance once, stopping on an obstacle or a new center-button press."""
    # Import after this module is loaded: the autonomous program imports dance.
    from main import DozerBehavior

    brick = EV3Brick()
    sensor = InfraredSensor(INFRARED_SENSOR_PORT)
    left = Motor(LEFT_TRACK_PORT, positive_direction=LEFT_TRACK_DIRECTION)
    right = Motor(RIGHT_TRACK_PORT, positive_direction=RIGHT_TRACK_DIRECTION)
    blade = Motor(BLADE_PORT, positive_direction=BLADE_DIRECTION)
    dozer = DozerBehavior(brick, sensor, left, right, blade)
    timer = StopWatch()

    try:
        dozer._brake_tracks()
        # Begin with the blade manually positioned just above the floor.
        blade.reset_angle(0)
        stop_ready = False
        while dozer.dance_beat < len(DANCE_ROUTINE) * 8:
            center_pressed = Button.CENTER in brick.buttons.pressed()
            if not center_pressed:
                stop_ready = True
            elif stop_ready:
                break
            if sensor.distance() <= OBSTACLE_DISTANCE:
                break
            now = timer.time()
            dozer._check_blade(now)
            if now >= dozer.deadline and dozer.blade_target is None:
                if dozer.deadline:
                    dozer.dance_beat += 1
                if dozer.dance_beat == len(DANCE_ROUTINE) * 8:
                    break
                step(dozer, now)
            wait(LOOP_DELAY)
    finally:
        dozer.stop()


if __name__ == "__main__":
    main()
