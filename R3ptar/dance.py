#!/usr/bin/env pybricks-micropython

"""Play a short tune while LEGO MINDSTORMS EV3 R3ptar dances."""

from pybricks.ev3devices import Motor
from pybricks.hubs import EV3Brick

from config import (
    BODY_DANCE_SPEED,
    DANCE_HEAD_TURN_SPEED as HEAD_TURN_SPEED,
    DANCE_REPEATS,
    DRIVE_MOTOR_PORT,
    HEAD_TURN_ANGLE,
    HEAD_TURN_MOTOR_PORT,
    MELODY,
)


def dance(brick, head_turn, drive):
    """Move R3ptar on each beat while playing the melody."""
    try:
        for unused in range(DANCE_REPEATS):
            for beat, (frequency, duration) in enumerate(MELODY):
                side = -1 if beat % 2 == 0 else 1

                # wait=False lets the head move while the note is sounding.
                head_turn.run_target(
                    HEAD_TURN_SPEED,
                    side * HEAD_TURN_ANGLE,
                    wait=False,
                )
                drive.run(side * BODY_DANCE_SPEED)
                brick.speaker.beep(frequency, duration)
    finally:
        # Also stop safely if the program is interrupted during the dance.
        drive.brake()
        head_turn.brake()

    # A normally completed dance ends with R3ptar looking straight ahead.
    head_turn.run_target(HEAD_TURN_SPEED, 0)
    head_turn.brake()


def main():
    brick = EV3Brick()
    head_turn = Motor(HEAD_TURN_MOTOR_PORT)
    drive = Motor(DRIVE_MOTOR_PORT)

    # R3ptar must begin with its head physically centered.
    head_turn.reset_angle(0)
    dance(brick, head_turn, drive)


if __name__ == "__main__":
    main()
