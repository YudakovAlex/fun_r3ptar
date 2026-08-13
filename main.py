#!/usr/bin/env pybricks-micropython

"""Autonomous, map-aware behavior for the LEGO MINDSTORMS EV3 R3ptar."""

from random import randint

from pybricks.ev3devices import InfraredSensor, Motor
from pybricks.hubs import EV3Brick
from pybricks.media.ev3dev import SoundFile
from pybricks.tools import StopWatch, wait

from config import (
    ALERT_GLANCE_TIME_MAX,
    ALERT_GLANCE_TIME_MIN,
    ALERT_TIME_MAX,
    ALERT_TIME_MIN,
    AUTONOMOUS_HEAD_TURN_SPEED as HEAD_TURN_SPEED,
    BACK_AWAY_TIME_MAX,
    BACK_AWAY_TIME_MIN,
    BITE_DIRECTION,
    BITE_FORWARD_TIME,
    BITE_RETURN_TIME,
    BITE_SPEED,
    CURIOUS_MOVE_TIME_MAX,
    CURIOUS_MOVE_TIME_MIN,
    DRIVE_MOTOR_PORT,
    ESCAPE_BACKUP_BONUS,
    ESCAPE_SCAN_TIME,
    FORWARD_PROGRESS_TIME,
    HEAD_BEND_MOTOR_PORT,
    HEAD_TURN_LIMIT,
    HEAD_TURN_MOTOR_PORT,
    INFRARED_SENSOR_PORT,
    LOOK_TIME_MAX,
    LOOK_TIME_MIN,
    LOOP_DELAY,
    MAP_CELL_MOTOR_DEGREES,
    MAP_SIZE,
    MAX_ESCAPE_LEVEL,
    MAX_MAP_VALUE,
    MIN_FORWARD_PROGRESS,
    MOVE_SPEED,
    OBSTACLE_CONFIRMATIONS,
    OBSTACLE_DISTANCE,
    RATTLE_TIME_MAX,
    RATTLE_TIME_MIN,
    REACTION_COOLDOWN,
    ROLLBACK_INTERVAL_MAX,
    ROLLBACK_INTERVAL_MIN,
    ROLLBACK_TIME_MAX,
    ROLLBACK_TIME_MIN,
    SOUND_PROGRESS_GRACE,
)


MAP_CENTER = MAP_SIZE // 2

NORTH = 0
DIRECTION_X = (0, 1, 1, 1, 0, -1, -1, -1)
DIRECTION_Y = (-1, -1, 0, 1, 1, 1, 0, -1)

EXPLORING = 0
ALERTING = 1
BITING = 2
CLOSING_MOUTH = 3
BACKING_AWAY = 4
ROLLING_BACK = 5
SEARCHING = 6

SLITHER_ANGLE = 38
SLITHER_STEP_TIME = 650
REPEATED_OBSTACLE_WINDOW = 6000


class SnakeBehavior:
    """Runs R3ptar's reactions and maintains a coarse in-memory map."""

    def __init__(self, brick, sensor, head_turn, head_bend, drive):
        self.brick = brick
        self.sensor = sensor
        self.head_turn = head_turn
        self.head_bend = head_bend
        self.drive = drive

        self.obstacles = [bytearray(MAP_SIZE) for unused in range(MAP_SIZE)]
        self.visits = [bytearray(MAP_SIZE) for unused in range(MAP_SIZE)]
        self.map_x = MAP_CENTER
        self.map_y = MAP_CENTER
        self.heading = NORTH
        self.travel_in_cell = 0
        self.last_drive_angle = drive.angle()
        self.visits[self.map_y][self.map_x] = 1

        self.state = EXPLORING
        self.state_deadline = 0
        self.obstacle_readings = 0
        self.last_obstacle_side = 0
        self.last_obstacle_time = -REPEATED_OBSTACLE_WINDOW
        self.ignore_obstacles_until = 0
        self.next_look = 0
        self.next_slither = 0
        self.slither_side = 1
        self.next_rattle = 0
        self.next_rollback = 0
        self.threat_side = 1
        self.alert_phase = 0
        self.look_phase = 0
        self.look_side = 1
        self.head_gesture_deadline = 0
        self.escape_level = 0
        self.search_phase = 0
        self.search_first_side = 1
        self.search_span = HEAD_TURN_LIMIT
        self.scan_left_distance = 0
        self.scan_right_distance = 0
        self.progress_angle = drive.angle()
        self.progress_check_after = 0

    def start(self, now):
        self.drive.run(MOVE_SPEED)
        self._choose_path(now, (-1, 0, 1))
        self.next_rattle = now + randint(RATTLE_TIME_MIN, RATTLE_TIME_MAX)
        self.next_rollback = now + randint(
            ROLLBACK_INTERVAL_MIN, ROLLBACK_INTERVAL_MAX
        )
        self._reset_progress_monitor(now)

    def step(self, now):
        """Advance the behavior once without waiting for a motor target."""
        self._update_position()

        if self.state == ALERTING:
            if now >= self.state_deadline:
                self._continue_alert(now)
            return

        if self.state == BITING:
            if now >= self.state_deadline:
                self._close_mouth(now)
            return

        if self.state == CLOSING_MOUTH:
            if now >= self.state_deadline:
                self._start_backing_away(now)
            return

        if self.state == BACKING_AWAY:
            if now >= self.state_deadline:
                self._start_escape_search(now)
            return

        if self.state == ROLLING_BACK:
            if now >= self.state_deadline:
                self._resume_exploring(now, (-1, 1))
            return

        if self.state == SEARCHING:
            if now >= self.state_deadline:
                self._continue_escape_search(now)
            return

        self._explore(now)

    def stop(self):
        self.drive.brake()
        self.head_turn.brake()
        self.head_bend.brake()

    def _explore(self, now):
        distance = self.sensor.distance()

        if distance <= OBSTACLE_DISTANCE:
            self.obstacle_readings += 1
        else:
            self.obstacle_readings = 0

        if (
            now >= self.ignore_obstacles_until
            and self.obstacle_readings >= OBSTACLE_CONFIRMATIONS
        ):
            obstacle_side = self._obstacle_side()
            repeated_on_same_side = (
                obstacle_side == self.last_obstacle_side
                and now - self.last_obstacle_time
                <= REPEATED_OBSTACLE_WINDOW
            )
            self.last_obstacle_side = obstacle_side
            self.last_obstacle_time = now

            if repeated_on_same_side:
                self._turn_away_from_repeated_obstacle(now, obstacle_side)
            else:
                self._start_alert(now)
            return

        if self._forward_is_stuck(now):
            self._start_stuck_recovery(now)
            return

        if now >= self.next_rollback:
            self._start_periodic_rollback(now)
            return

        if self.look_phase:
            self._continue_curious_look(now)
        elif now >= self.next_look:
            self._start_curious_look(now)
        else:
            self._continue_slither(now)

        if now >= self.next_rattle:
            # Stop while making a long sound so R3ptar does not travel blind.
            self.drive.brake()
            self.brick.speaker.play_file(SoundFile.SNAKE_RATTLE)
            self.drive.run(MOVE_SPEED)
            self._reset_progress_monitor(now, SOUND_PROGRESS_GRACE)
            self.next_rattle = now + randint(
                RATTLE_TIME_MIN, RATTLE_TIME_MAX
            )

    def _start_alert(self, now):
        self._mark_obstacle_ahead()
        self.drive.brake()
        self.obstacle_readings = 0
        self.look_phase = 0
        self.escape_level = min(MAX_ESCAPE_LEVEL, self.escape_level + 1)
        self.threat_side = -1 if randint(0, 1) == 0 else 1
        self.alert_phase = 0
        # Open the mouth as the hiss starts and make the lunge pronounced.
        self.head_bend.run_time(
            BITE_DIRECTION * BITE_SPEED,
            BITE_FORWARD_TIME * 2,
            wait=False,
        )

        # Freeze and snap the head toward the threat before striking.
        alert_angle = self.threat_side * randint(15, 32)
        self.head_turn.run_target(
            HEAD_TURN_SPEED, alert_angle, wait=False
        )
        self.state = ALERTING
        self.state_deadline = now + randint(ALERT_TIME_MIN, ALERT_TIME_MAX)
        self.brick.speaker.play_file(SoundFile.SNAKE_HISS)

    def _obstacle_side(self):
        """Return the side toward which the sensor-facing head is turned."""
        return -1 if self.head_turn.angle() < 0 else 1

    def _turn_away_from_repeated_obstacle(self, now, obstacle_side):
        """Skip another attack and commit to a new direction."""
        self._mark_obstacle_ahead()
        self.drive.brake()
        self.obstacle_readings = 0
        self.look_phase = 0
        self.escape_level = min(MAX_ESCAPE_LEVEL, self.escape_level + 1)

        turn_side = -obstacle_side
        turn_steps = min(4, self.escape_level + 1)
        self.heading = (self.heading + turn_side * turn_steps) % 8
        self.travel_in_cell = 0
        self.head_turn.run_target(
            HEAD_TURN_SPEED + 100,
            turn_side * HEAD_TURN_LIMIT,
            wait=False,
        )
        self.slither_side = obstacle_side
        self.next_slither = now + REACTION_COOLDOWN
        self.next_look = now + LOOK_TIME_MIN
        self.ignore_obstacles_until = now + REACTION_COOLDOWN
        self.drive.run(MOVE_SPEED)
        self._reset_progress_monitor(now)
        self.next_rollback = now + randint(
            ROLLBACK_INTERVAL_MIN, ROLLBACK_INTERVAL_MAX
        )

    def _continue_alert(self, now):
        """Make two wary head feints before committing to the bite."""
        if self.alert_phase == 0:
            self.head_turn.run_target(
                HEAD_TURN_SPEED + 50,
                -self.threat_side * randint(8, 22),
                wait=False,
            )
            self.alert_phase = 1
            self.state_deadline = now + randint(
                ALERT_GLANCE_TIME_MIN, ALERT_GLANCE_TIME_MAX
            )
            return

        if self.alert_phase == 1:
            self.head_turn.run_target(
                HEAD_TURN_SPEED + 80,
                self.threat_side * randint(28, HEAD_TURN_LIMIT),
                wait=False,
            )
            self.alert_phase = 2
            self.state_deadline = now + randint(
                ALERT_GLANCE_TIME_MIN, ALERT_GLANCE_TIME_MAX
            )
            return

        self._start_bite(now)

    def _start_bite(self, now):
        # Dart toward the center line with the mouth already open.
        self.head_turn.run_target(
            HEAD_TURN_SPEED + 100,
            randint(-8, 8),
            wait=False,
        )
        self.state = BITING
        self.state_deadline = now + BITE_FORWARD_TIME

    def _close_mouth(self, now):
        # Recoil to a semi-random side while returning the biting mechanism.
        recoil_angle = self.threat_side * randint(30, HEAD_TURN_LIMIT)
        self.head_turn.run_target(
            HEAD_TURN_SPEED, recoil_angle, wait=False
        )
        self.head_bend.run_time(
            -BITE_DIRECTION * BITE_SPEED,
            BITE_RETURN_TIME * 2,
            wait=False,
        )
        self.state = CLOSING_MOUTH
        self.state_deadline = now + BITE_RETURN_TIME * 2

    def _start_backing_away(self, now):
        self.head_bend.brake()
        self.drive.run(-MOVE_SPEED)
        self.state = BACKING_AWAY
        self.state_deadline = now + randint(
            BACK_AWAY_TIME_MIN, BACK_AWAY_TIME_MAX
        ) + (self.escape_level - 1) * ESCAPE_BACKUP_BONUS

    def _start_stuck_recovery(self, now):
        """Recover when the drive encoder shows that forward motion failed."""
        self._mark_obstacle_ahead()
        self.look_phase = 0
        self.escape_level = min(MAX_ESCAPE_LEVEL, self.escape_level + 1)
        self.threat_side = -1 if randint(0, 1) == 0 else 1
        self.drive.brake()
        self.head_turn.run_target(
            HEAD_TURN_SPEED + 100,
            self.threat_side * HEAD_TURN_LIMIT,
            wait=False,
        )
        self.brick.speaker.play_file(SoundFile.SNAKE_RATTLE)
        self.next_rattle = now + randint(RATTLE_TIME_MIN, RATTLE_TIME_MAX)
        self._start_backing_away(now)

    def _start_escape_search(self, now):
        """Stop and inspect both sides before choosing a wider escape path."""
        self.drive.brake()
        self.state = SEARCHING
        self.search_phase = 0
        self.search_first_side = -1 if randint(0, 1) == 0 else 1
        self.search_span = min(
            HEAD_TURN_LIMIT, 32 + self.escape_level * 6
        )
        self.head_turn.run_target(
            HEAD_TURN_SPEED + 80,
            self.search_first_side * self.search_span,
            wait=False,
        )
        self.state_deadline = now + ESCAPE_SCAN_TIME

        if self.escape_level >= 2:
            self.brick.speaker.play_file(SoundFile.SNAKE_RATTLE)
            self.next_rattle = now + randint(
                RATTLE_TIME_MIN, RATTLE_TIME_MAX
            )

    def _continue_escape_search(self, now):
        if self.search_phase == 0:
            self._remember_scan(self.search_first_side)
            self.head_turn.run_target(
                HEAD_TURN_SPEED + 80,
                -self.search_first_side * self.search_span,
                wait=False,
            )
            self.search_phase = 1
            self.state_deadline = now + ESCAPE_SCAN_TIME
            return

        self._remember_scan(-self.search_first_side)
        self._finish_escape_search(now)

    def _remember_scan(self, side):
        if side < 0:
            self.scan_left_distance = self.sensor.distance()
        else:
            self.scan_right_distance = self.sensor.distance()

    def _finish_escape_search(self, now):
        """Take a sharper turn after each consecutive failed route."""
        turn_steps = min(4, self.escape_level + 1)
        left_score = self._escape_score(
            -turn_steps, self.scan_left_distance
        )
        right_score = self._escape_score(
            turn_steps, self.scan_right_distance
        )

        if left_score == right_score:
            side = -1 if randint(0, 1) == 0 else 1
        else:
            side = -1 if left_score < right_score else 1

        relative_turn = side * turn_steps
        self.heading = (self.heading + relative_turn) % 8
        self.travel_in_cell = 0
        minimum_escape_angle = min(
            HEAD_TURN_LIMIT, 34 + self.escape_level * 5
        )
        escape_target = side * randint(
            minimum_escape_angle, HEAD_TURN_LIMIT
        )
        self.head_turn.run_target(
            HEAD_TURN_SPEED + 100,
            escape_target,
            wait=False,
        )
        self.slither_side = -side
        self.next_slither = now + SLITHER_STEP_TIME
        self.state = EXPLORING
        self.ignore_obstacles_until = now + REACTION_COOLDOWN
        self.obstacle_readings = 0
        self.look_phase = 0
        # Keep the head committed to wider escape turns for longer.
        self.next_look = now + LOOK_TIME_MIN + self.escape_level * 450
        self.drive.run(MOVE_SPEED)
        self._reset_progress_monitor(now)
        self.next_rollback = now + randint(
            ROLLBACK_INTERVAL_MIN, ROLLBACK_INTERVAL_MAX
        )

    def _escape_score(self, relative_turn, scan_distance):
        direction = (self.heading + relative_turn) % 8
        score = self._direction_score(direction)
        score += 100 - scan_distance
        if scan_distance <= OBSTACLE_DISTANCE:
            score += 200
        return score

    def _start_periodic_rollback(self, now):
        """Back up briefly to escape low objects outside the sensor's view."""
        self.look_phase = 0
        self.drive.run(-MOVE_SPEED)
        self.head_turn.run_target(
            HEAD_TURN_SPEED,
            randint(-HEAD_TURN_LIMIT // 2, HEAD_TURN_LIMIT // 2),
            wait=False,
        )
        self.state = ROLLING_BACK
        self.state_deadline = now + randint(
            ROLLBACK_TIME_MIN, ROLLBACK_TIME_MAX
        )

    def _resume_exploring(self, now, possible_turns):
        self.state = EXPLORING
        self.ignore_obstacles_until = now + REACTION_COOLDOWN
        self.obstacle_readings = 0
        self._choose_path(now, possible_turns)
        self.drive.run(MOVE_SPEED)
        self._reset_progress_monitor(now)
        self.next_rollback = now + randint(
            ROLLBACK_INTERVAL_MIN, ROLLBACK_INTERVAL_MAX
        )

    def _start_curious_look(self, now):
        """Begin a small left-right investigation while continuing forward."""
        self.look_side = -1 if randint(0, 1) == 0 else 1
        self.look_phase = 1
        self.head_turn.run_target(
            HEAD_TURN_SPEED - 40,
            self.look_side * randint(16, 30),
            wait=False,
        )
        # A slight nod makes ordinary exploration less mechanical.
        self.head_bend.run_target(
            BITE_SPEED // 2,
            BITE_DIRECTION * randint(5, 11),
            wait=False,
        )
        self.head_gesture_deadline = now + randint(
            CURIOUS_MOVE_TIME_MIN, CURIOUS_MOVE_TIME_MAX
        )

    def _continue_curious_look(self, now):
        if now < self.head_gesture_deadline:
            return

        if self.look_phase == 1:
            self.head_turn.run_target(
                HEAD_TURN_SPEED + 20,
                -self.look_side * randint(20, 38),
                wait=False,
            )
            self.head_bend.run_target(BITE_SPEED // 2, 0, wait=False)
            self.look_phase = 2
            self.head_gesture_deadline = now + randint(
                CURIOUS_MOVE_TIME_MIN, CURIOUS_MOVE_TIME_MAX
            )
            return

        self.look_phase = 0
        self._choose_path(now, (-1, 0, 1))

    def _continue_slither(self, now):
        """Sweep the steering from side to side to make an S-shaped crawl."""
        if now < self.next_slither:
            return

        self.head_turn.run_target(
            HEAD_TURN_SPEED,
            self.slither_side * SLITHER_ANGLE,
            wait=False,
        )
        self.slither_side = -self.slither_side
        self.next_slither = now + SLITHER_STEP_TIME

    def _forward_is_stuck(self, now):
        if now < self.progress_check_after:
            return False

        current_angle = self.drive.angle()
        progress = abs(current_angle - self.progress_angle)
        self.progress_angle = current_angle
        self.progress_check_after = now + FORWARD_PROGRESS_TIME

        if progress < MIN_FORWARD_PROGRESS:
            return True

        if self.escape_level > 0:
            self.escape_level -= 1
        return False

    def _reset_progress_monitor(self, now, delay=FORWARD_PROGRESS_TIME):
        self.progress_angle = self.drive.angle()
        self.progress_check_after = now + delay

    def _choose_path(self, now, possible_turns):
        """Prefer an open, less-visited direction, with small random variation."""
        best_turn = possible_turns[0]
        best_score = 100000

        for relative_turn in possible_turns:
            direction = (self.heading + relative_turn) % 8
            score = self._direction_score(direction) + randint(0, 8)
            if relative_turn == 0:
                score -= 2
            if score < best_score:
                best_score = score
                best_turn = relative_turn

        self.heading = (self.heading + best_turn) % 8
        self.travel_in_cell = 0

        if best_turn == 0:
            target = randint(-12, 12)
        else:
            target = (1 if best_turn > 0 else -1) * randint(
                28, HEAD_TURN_LIMIT
            )

        self.head_turn.run_target(HEAD_TURN_SPEED, target, wait=False)
        if target > 0:
            self.slither_side = -1
        elif target < 0:
            self.slither_side = 1
        self.next_slither = now + SLITHER_STEP_TIME
        self.next_look = now + randint(LOOK_TIME_MIN, LOOK_TIME_MAX)

    def _direction_score(self, direction):
        """Score two cells ahead using remembered obstacles and visits."""
        x = self.map_x
        y = self.map_y
        score = 0

        for distance in (1, 2):
            x += DIRECTION_X[direction]
            y += DIRECTION_Y[direction]
            if not self._inside_map(x, y):
                return 1000

            score += self.obstacles[y][x] * (35 // distance)
            score += self.visits[y][x] * (5 // distance)

        return score

    def _update_position(self):
        """Estimate map position from drive rotation and current heading."""
        current_angle = self.drive.angle()
        angle_change = current_angle - self.last_drive_angle
        self.last_drive_angle = current_angle

        if self.state not in (EXPLORING, BACKING_AWAY, ROLLING_BACK):
            return

        self.travel_in_cell += angle_change
        while self.travel_in_cell >= MAP_CELL_MOTOR_DEGREES:
            self._move_one_cell(self.heading)
            self.travel_in_cell -= MAP_CELL_MOTOR_DEGREES

        while self.travel_in_cell <= -MAP_CELL_MOTOR_DEGREES:
            self._move_one_cell((self.heading + 4) % 8)
            self.travel_in_cell += MAP_CELL_MOTOR_DEGREES

    def _move_one_cell(self, direction):
        x = self.map_x + DIRECTION_X[direction]
        y = self.map_y + DIRECTION_Y[direction]
        if not self._inside_map(x, y):
            return

        self.map_x = x
        self.map_y = y
        self.obstacles[y][x] = 0
        if self.visits[y][x] < MAX_MAP_VALUE:
            self.visits[y][x] += 1

    def _mark_obstacle_ahead(self):
        x, y = self._cell_ahead(self.heading)
        if self._inside_map(x, y):
            self.obstacles[y][x] = min(
                MAX_MAP_VALUE, self.obstacles[y][x] + 3
            )

    def _cell_ahead(self, direction):
        return (
            self.map_x + DIRECTION_X[direction],
            self.map_y + DIRECTION_Y[direction],
        )

    @staticmethod
    def _inside_map(x, y):
        return 0 <= x < MAP_SIZE and 0 <= y < MAP_SIZE


def main():
    brick = EV3Brick()
    sensor = InfraredSensor(INFRARED_SENSOR_PORT)
    head_turn = Motor(HEAD_TURN_MOTOR_PORT)
    drive = Motor(DRIVE_MOTOR_PORT)
    head_bend = Motor(HEAD_BEND_MOTOR_PORT)

    # Start with the head centered and raised/resting.
    head_turn.reset_angle(0)
    head_bend.reset_angle(0)

    timer = StopWatch()
    behavior = SnakeBehavior(
        brick, sensor, head_turn, head_bend, drive
    )
    behavior.start(timer.time())

    try:
        while True:
            behavior.step(timer.time())
            wait(LOOP_DELAY)
    finally:
        behavior.stop()


if __name__ == "__main__":
    main()
