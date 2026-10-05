#!/usr/bin/env pybricks-micropython

"""Basic autonomous behavior for the LEGO MINDSTORMS EV3 R3ptar."""

from random import randint

from pybricks.ev3devices import InfraredSensor, Motor
from pybricks.hubs import EV3Brick
from pybricks.media.ev3dev import SoundFile
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait


# Adjust these values if R3ptar moves too quickly or reacts too soon.
OBSTACLE_DISTANCE = 45  # Infrared distance: 0 is closest, 100 is farthest.
MOVE_SPEED = 500
HEAD_TURN_SPEED = 250
HEAD_TURN_ANGLE = 45
BITE_SPEED = 700
BITE_DIRECTION = -1

SCAN_TIME = 1800
BITE_FORWARD_TIME = 250
BITE_RETURN_TIME = 250
BACK_AWAY_TIME = 900
REACTION_COOLDOWN = 1000
RATTLE_TIME_MIN = 10000
RATTLE_TIME_MAX = 18000
LOOP_DELAY = 50

EXPLORING = 0
BITING = 1
CLOSING_MOUTH = 2
BACKING_AWAY = 3


ev3 = EV3Brick()
sensor = InfraredSensor(Port.S4)
head_turn_motor = Motor(Port.A)
move_motor = Motor(Port.B)
head_bend_motor = Motor(Port.D)


def start_bite():
    """Start an attack without waiting for the jaw motor to reach a target."""
    move_motor.brake()
    head_bend_motor.run_time(
        BITE_DIRECTION * BITE_SPEED, BITE_FORWARD_TIME, wait=False
    )
    ev3.speaker.play_file(SoundFile.SNAKE_HISS)


def main():
    # R3ptar should start with its head centered and raised/resting.
    head_turn_motor.reset_angle(0)
    head_bend_motor.reset_angle(0)

    timer = StopWatch()
    last_scan = 0
    turn_angle = HEAD_TURN_ANGLE
    next_rattle = randint(RATTLE_TIME_MIN, RATTLE_TIME_MAX)
    ignore_obstacles_until = 0
    state = EXPLORING
    state_started = 0

    move_motor.run(MOVE_SPEED)
    head_turn_motor.run_target(HEAD_TURN_SPEED, turn_angle, wait=False)

    try:
        while True:
            now = timer.time()

            if state == BITING and now - state_started >= BITE_FORWARD_TIME:
                head_bend_motor.run(-BITE_DIRECTION * BITE_SPEED)
                state = CLOSING_MOUTH
                state_started = now

            elif (
                state == CLOSING_MOUTH
                and now - state_started >= BITE_RETURN_TIME
            ):
                head_bend_motor.brake()
                move_motor.run(-MOVE_SPEED)
                state = BACKING_AWAY
                state_started = now

            elif (
                state == BACKING_AWAY
                and now - state_started >= BACK_AWAY_TIME
            ):
                turn_angle = -turn_angle
                head_turn_motor.run_target(
                    HEAD_TURN_SPEED, turn_angle, wait=False
                )
                move_motor.run(MOVE_SPEED)
                state = EXPLORING
                last_scan = now
                ignore_obstacles_until = now + REACTION_COOLDOWN

            elif (
                state == EXPLORING
                and now >= ignore_obstacles_until
                and sensor.distance() <= OBSTACLE_DISTANCE
            ):
                start_bite()
                state = BITING
                state_started = timer.time()

            elif state == EXPLORING and now - last_scan >= SCAN_TIME:
                turn_angle = -turn_angle
                head_turn_motor.run_target(
                    HEAD_TURN_SPEED, turn_angle, wait=False
                )
                last_scan = now

            if state == EXPLORING and now >= next_rattle:
                ev3.speaker.play_file(SoundFile.SNAKE_RATTLE)
                next_rattle = timer.time() + randint(
                    RATTLE_TIME_MIN, RATTLE_TIME_MAX
                )

            wait(LOOP_DELAY)
    finally:
        move_motor.brake()
        head_turn_motor.brake()
        head_bend_motor.brake()


main()
