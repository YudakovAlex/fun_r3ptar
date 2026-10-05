#!/usr/bin/env pybricks-micropython

"""A cheerful, autonomous construction worker for LEGO EV3 Robodoz3r."""

from random import randint

import dance

from pybricks.ev3devices import InfraredSensor, Motor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Button, Color, Stop
from pybricks.tools import StopWatch, wait

from config import (
    BACKUP_TIME,
    BLADE_DIRECTION,
    BLADE_LIFT_ANGLE,
    BLADE_PORT,
    BLADE_SPEED,
    BLADE_MOVE_TIME,
    DANCE_INTERVAL_MAX,
    DANCE_INTERVAL_MIN,
    DRIVE_SPEED,
    GREETING_TIME,
    INFRARED_SENSOR_PORT,
    LEFT_TRACK_DIRECTION,
    LEFT_TRACK_PORT,
    LOOP_DELAY,
    OBSTACLE_DISTANCE,
    RIGHT_TRACK_DIRECTION,
    RIGHT_TRACK_PORT,
    TURN_SPEED,
    TURN_TIME,
)


GREETING = "greeting"
LOWERING = "lowering"
CRUISING = "cruising"
BACKING = "backing"
TURNING = "turning"
DANCING = "dancing"


class DozerBehavior:
    def __init__(self, brick, sensor, left, right, blade):
        self.brick = brick
        self.sensor = sensor
        self.left = left
        self.right = right
        self.blade = blade
        self.state = GREETING
        self.deadline = 0
        self.blade_target = None
        self.blade_deadline = 0
        self.next_dance = 0
        self.next_beep = 0
        self.dance_beat = 0
        self.escape_attempts = 0
        self.turn_side = 1

    def start(self, now):
        self._brake_tracks()
        # Place the blade just above the floor before starting.
        self.blade.reset_angle(0)
        self._show("READY TO BUILD!", "^   ^", Color.GREEN)
        self._blade_to(BLADE_LIFT_ANGLE, now)
        self.brick.speaker.beep(784, 60)
        self.state = GREETING
        self.deadline = now + GREETING_TIME
        self._schedule_dance(now)

    def step(self, now):
        """Advance one small action so the main loop can keep checking stop."""
        self._check_blade(now)

        if self.state == CRUISING:
            if self.sensor.distance() <= OBSTACLE_DISTANCE:
                self._back_away(now, "WHOA! DETOUR!")
            elif now >= self.next_dance:
                self.state = DANCING
                self.dance_beat = 0
                dance.step(self, now)
            return

        if self.state == DANCING:
            if self.sensor.distance() <= OBSTACLE_DISTANCE:
                self._back_away(now, "EXCUSE ME!")
            elif now >= self.deadline and self.blade_target is None:
                self.dance_beat += 1
                if self.dance_beat == len(dance.DANCE_ROUTINE) * 8:
                    self._schedule_dance(now)
                    self._cruise(now)
                else:
                    dance.step(self, now)
            return

        if self.state == BACKING and now < self.deadline:
            if now >= self.next_beep:
                self.brick.speaker.beep(440, 40)
                self.next_beep = now + 300
            return

        if now < self.deadline:
            return
        if self.blade_target is not None:
            return

        if self.state == GREETING:
            self._blade_to(0, now)
            self.brick.speaker.beep(1047, 60)
            self.state = LOWERING
            self.deadline = now + GREETING_TIME
        elif self.state in (LOWERING, TURNING):
            self._cruise(now)
        elif self.state == BACKING:
            self._brake_tracks()
            self._blade_to(0, now)
            self._show("NEW PLAN!", "o   O", Color.ORANGE)
            duration = TURN_TIME + (self.escape_attempts - 1) * 300
            self._turn(self.turn_side, duration)
            self.state = TURNING
            self.deadline = now + duration

    def stop(self):
        self._brake_tracks()
        self.blade.brake()

    def _brake_tracks(self):
        self.left.brake()
        self.right.brake()

    def _show(self, message, face, color):
        self.brick.screen.clear()
        self.brick.screen.print(face)
        self.brick.screen.print(message)
        self.brick.light.on(color)

    def _blade_to(self, target, now):
        if self.blade_target == target:
            return
        self.blade.run_target(BLADE_SPEED, target, then=Stop.BRAKE, wait=False)
        self.blade_target = target
        self.blade_deadline = now + BLADE_MOVE_TIME

    def _check_blade(self, now):
        if self.blade_target is None:
            return
        if now >= self.blade_deadline:
            self.blade.brake()
            self.blade_target = None

    def _cruise(self, now):
        self._brake_tracks()
        # Check again after every maneuver, before applying forward power.
        if self.sensor.distance() <= OBSTACLE_DISTANCE:
            self._back_away(now, "STILL BLOCKED!")
            return
        self._show("ON THE JOB!", "o   o", Color.GREEN)
        self.left.run(DRIVE_SPEED)
        self.right.run(DRIVE_SPEED)
        self.state = CRUISING

    def _back_away(self, now, message):
        self._brake_tracks()
        if self.escape_attempts == 0:
            self.turn_side = -1 if randint(0, 1) == 0 else 1
        self.escape_attempts = min(3, self.escape_attempts + 1)
        self._show(message, "O   O", Color.ORANGE)
        self._blade_to(BLADE_LIFT_ANGLE, now)
        self.brick.speaker.beep(330, 60)
        duration = BACKUP_TIME + (self.escape_attempts - 1) * 150
        self.left.run_time(-DRIVE_SPEED, duration, then=Stop.BRAKE, wait=False)
        self.right.run_time(-DRIVE_SPEED, duration, then=Stop.BRAKE, wait=False)
        self.state = BACKING
        self.deadline = now + duration
        self.next_beep = now + 300
        self._schedule_dance(now)

    def _turn(self, side, duration):
        self.left.run_time(side * TURN_SPEED, duration, then=Stop.BRAKE, wait=False)
        self.right.run_time(-side * TURN_SPEED, duration, then=Stop.BRAKE, wait=False)

    def _schedule_dance(self, now):
        self.next_dance = now + randint(DANCE_INTERVAL_MIN, DANCE_INTERVAL_MAX)


def main():
    brick = EV3Brick()
    sensor = InfraredSensor(INFRARED_SENSOR_PORT)
    left = Motor(LEFT_TRACK_PORT, positive_direction=LEFT_TRACK_DIRECTION)
    right = Motor(RIGHT_TRACK_PORT, positive_direction=RIGHT_TRACK_DIRECTION)
    blade = Motor(BLADE_PORT, positive_direction=BLADE_DIRECTION)
    behavior = DozerBehavior(brick, sensor, left, right, blade)
    timer = StopWatch()

    try:
        behavior.start(timer.time())
        # Ignore the center press used to launch the program until released.
        stop_ready = False
        while True:
            center_pressed = Button.CENTER in brick.buttons.pressed()
            if not center_pressed:
                stop_ready = True
            elif stop_ready:
                break
            behavior.step(timer.time())
            wait(LOOP_DELAY)
    finally:
        behavior.stop()


if __name__ == "__main__":
    main()
