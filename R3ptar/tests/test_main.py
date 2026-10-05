import importlib
import sys
import types
import unittest
from unittest.mock import patch


class FakeMotor:
    def __init__(self, port=None):
        self.angle_value = 0
        self.commands = []
        self.speed = 0

    def angle(self):
        return self.angle_value

    def tick(self, milliseconds):
        self.angle_value += self.speed * milliseconds // 1000

    def run(self, speed):
        self.speed = speed
        self.commands.append(("run", speed))

    def run_time(self, speed, duration, wait=True):
        self.commands.append(("run_time", speed, duration, wait))

    def run_target(self, speed, target, wait=True):
        self.commands.append(("run_target", speed, target, wait))

    def reset_angle(self, angle):
        self.angle_value = angle

    def brake(self):
        self.speed = 0
        self.commands.append(("brake",))


class FakeSensor:
    def __init__(self, distance=100):
        self.value = distance

    def distance(self):
        return self.value


class FakeSpeaker:
    def __init__(self):
        self.sounds = []

    def play_file(self, sound):
        self.sounds.append(sound)


class FakeBrick:
    def __init__(self):
        self.speaker = FakeSpeaker()


def install_pybricks_stubs():
    modules = {
        "pybricks": types.ModuleType("pybricks"),
        "pybricks.ev3devices": types.ModuleType("pybricks.ev3devices"),
        "pybricks.hubs": types.ModuleType("pybricks.hubs"),
        "pybricks.media": types.ModuleType("pybricks.media"),
        "pybricks.media.ev3dev": types.ModuleType("pybricks.media.ev3dev"),
        "pybricks.parameters": types.ModuleType("pybricks.parameters"),
        "pybricks.tools": types.ModuleType("pybricks.tools"),
    }

    modules["pybricks.ev3devices"].InfraredSensor = FakeSensor
    modules["pybricks.ev3devices"].Motor = FakeMotor
    modules["pybricks.hubs"].EV3Brick = FakeBrick
    modules["pybricks.media.ev3dev"].SoundFile = types.SimpleNamespace(
        SNAKE_HISS="hiss", SNAKE_RATTLE="rattle"
    )
    modules["pybricks.parameters"].Port = types.SimpleNamespace(
        S4="S4", A="A", B="B", D="D"
    )
    modules["pybricks.tools"].StopWatch = object
    modules["pybricks.tools"].wait = lambda milliseconds: None
    sys.modules.update(modules)


install_pybricks_stubs()
robot = importlib.import_module("main")


class SnakeBehaviorTests(unittest.TestCase):
    def create_behavior(self, sensor_distance):
        self.brick = FakeBrick()
        self.sensor = FakeSensor(sensor_distance)
        self.head_turn = FakeMotor()
        self.head_bend = FakeMotor()
        self.drive = FakeMotor()
        behavior = robot.SnakeBehavior(
            self.brick,
            self.sensor,
            self.head_turn,
            self.head_bend,
            self.drive,
        )
        behavior.start(0)
        return behavior

    def run_for(self, behavior, duration):
        for now in range(0, duration, robot.LOOP_DELAY):
            self.drive.tick(robot.LOOP_DELAY)
            behavior.step(now)

    def test_main_uses_configured_hardware_ports(self):
        class FakeStopWatch:
            def time(self):
                return 0

        with (
            patch.object(
                robot, "InfraredSensor", return_value=FakeSensor()
            ) as sensor_type,
            patch.object(robot, "Motor", side_effect=FakeMotor) as motor_type,
            patch.object(robot, "StopWatch", FakeStopWatch),
            patch.object(robot, "wait", side_effect=KeyboardInterrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            robot.main()

        sensor_type.assert_called_once_with(robot.INFRARED_SENSOR_PORT)
        self.assertEqual(
            [call.args[0] for call in motor_type.call_args_list],
            [
                robot.HEAD_TURN_MOTOR_PORT,
                robot.DRIVE_MOTOR_PORT,
                robot.HEAD_BEND_MOTOR_PORT,
            ],
        )

    def test_continuously_blocked_sensor_turns_instead_of_repeating_reaction(self):
        behavior = self.create_behavior(20)

        self.run_for(behavior, 9000)

        forward_runs = [
            command
            for command in self.drive.commands
            if command == ("run", robot.MOVE_SPEED)
        ]
        backward_runs = [
            command
            for command in self.drive.commands
            if command == ("run", -robot.MOVE_SPEED)
        ]
        self.assertGreaterEqual(len(forward_runs), 3)
        self.assertEqual(len(backward_runs), 1)
        self.assertEqual(self.brick.speaker.sounds.count("hiss"), 1)

    def test_obstacle_is_recorded_in_the_map(self):
        behavior = self.create_behavior(20)
        obstacle_x, obstacle_y = behavior._cell_ahead(behavior.heading)

        self.run_for(behavior, 200)

        self.assertGreater(behavior.obstacles[obstacle_y][obstacle_x], 0)

    def test_repeated_obstacle_on_same_side_turns_away_without_hissing(self):
        behavior = self.create_behavior(20)
        behavior.last_obstacle_side = -1
        behavior.last_obstacle_time = 100
        behavior.obstacle_readings = robot.OBSTACLE_CONFIRMATIONS - 1
        self.head_turn.angle_value = -20
        original_heading = behavior.heading

        behavior.step(200)

        self.assertEqual(behavior.state, robot.EXPLORING)
        self.assertEqual(behavior.heading, (original_heading + 2) % 8)
        self.assertEqual(self.brick.speaker.sounds, [])
        self.assertEqual(self.drive.speed, robot.MOVE_SPEED)
        self.assertEqual(
            self.head_turn.commands[-1],
            (
                "run_target",
                robot.HEAD_TURN_SPEED + 100,
                robot.HEAD_TURN_LIMIT,
                False,
            ),
        )

    def test_hiss_opens_mouth_with_extended_forward_motion(self):
        behavior = self.create_behavior(20)

        behavior._start_alert(100)

        self.assertIn("hiss", self.brick.speaker.sounds)
        self.assertIn(
            (
                "run_time",
                robot.BITE_DIRECTION * robot.BITE_SPEED,
                robot.BITE_FORWARD_TIME * 2,
                False,
            ),
            self.head_bend.commands,
        )

        behavior._close_mouth(200)

        self.assertEqual(
            self.head_bend.commands[-1],
            (
                "run_time",
                -robot.BITE_DIRECTION * robot.BITE_SPEED,
                robot.BITE_RETURN_TIME * 2,
                False,
            ),
        )
        self.assertEqual(
            behavior.state_deadline, 200 + robot.BITE_RETURN_TIME * 2
        )

    def test_path_planner_avoids_a_remembered_obstacle(self):
        behavior = self.create_behavior(100)
        blocked_heading = behavior.heading
        obstacle_x, obstacle_y = behavior._cell_ahead(blocked_heading)
        behavior.obstacles[obstacle_y][obstacle_x] = robot.MAX_MAP_VALUE

        with patch.object(robot, "randint", side_effect=lambda low, high: low):
            behavior._choose_path(100, (-1, 0, 1))

        self.assertNotEqual(behavior.heading, blocked_heading)

    def test_stalled_drive_starts_aggressive_recovery(self):
        behavior = self.create_behavior(100)

        # Advance time without advancing the drive encoder.
        for now in range(
            0,
            robot.FORWARD_PROGRESS_TIME + robot.LOOP_DELAY * 2,
            robot.LOOP_DELAY,
        ):
            behavior.step(now)

        self.assertEqual(behavior.state, robot.BACKING_AWAY)
        self.assertEqual(behavior.escape_level, 1)
        self.assertIn(("run", -robot.MOVE_SPEED), self.drive.commands)
        self.assertIn("rattle", self.brick.speaker.sounds)

    def test_curious_look_sweeps_both_sides_and_nods(self):
        behavior = self.create_behavior(100)
        behavior.next_look = 0
        initial_turn_commands = len(self.head_turn.commands)

        self.run_for(behavior, 1000)

        turn_commands = self.head_turn.commands[initial_turn_commands:]
        targets = [
            command[2]
            for command in turn_commands
            if command[0] == "run_target"
        ]
        self.assertGreaterEqual(len(targets), 2)
        self.assertLess(targets[0] * targets[1], 0)
        self.assertTrue(
            any(command[0] == "run_target" for command in self.head_bend.commands)
        )

    def test_forward_drive_slithers_from_side_to_side(self):
        behavior = self.create_behavior(100)
        behavior.next_look = 10000
        initial_turn_commands = len(self.head_turn.commands)

        self.run_for(behavior, robot.SLITHER_STEP_TIME * 4)

        targets = [
            command[2]
            for command in self.head_turn.commands[initial_turn_commands:]
            if command[0] == "run_target"
        ]
        self.assertGreaterEqual(len(targets), 3)
        self.assertEqual(
            [abs(target) for target in targets[:3]],
            [robot.SLITHER_ANGLE] * 3,
        )
        self.assertLess(targets[0] * targets[1], 0)
        self.assertLess(targets[1] * targets[2], 0)
        self.assertEqual(self.drive.speed, robot.MOVE_SPEED)

    def test_repeated_failed_routes_escalate_to_a_reversal(self):
        behavior = self.create_behavior(100)
        original_heading = behavior.heading
        behavior.escape_level = robot.MAX_ESCAPE_LEVEL
        behavior.scan_left_distance = 20
        behavior.scan_right_distance = 20

        with patch.object(robot, "randint", side_effect=lambda low, high: low):
            behavior._finish_escape_search(100)

        self.assertEqual(behavior.heading, (original_heading + 4) % 8)

    def test_periodic_rollback_returns_to_exploring(self):
        behavior = self.create_behavior(100)
        behavior.next_rollback = 100

        self.run_for(behavior, 2500)

        self.assertIn(("run", -robot.MOVE_SPEED), self.drive.commands)
        self.assertEqual(behavior.state, robot.EXPLORING)
        self.assertEqual(self.drive.speed, robot.MOVE_SPEED)


if __name__ == "__main__":
    unittest.main()
