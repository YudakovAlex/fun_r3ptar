import importlib
import sys
import types
import unittest
from unittest.mock import patch


class FakeMotor:
    def __init__(self, port=None):
        self.port = port
        self.commands = []

    def run(self, speed):
        self.commands.append(("run", speed))

    def run_target(self, speed, target, wait=True):
        self.commands.append(("run_target", speed, target, wait))

    def reset_angle(self, angle):
        self.commands.append(("reset_angle", angle))

    def brake(self):
        self.commands.append(("brake",))


class FakeSpeaker:
    def __init__(self, fail_after=None):
        self.tones = []
        self.fail_after = fail_after

    def beep(self, frequency, duration):
        self.tones.append((frequency, duration))
        if self.fail_after == len(self.tones):
            raise RuntimeError("speaker failed")


class FakeBrick:
    def __init__(self, fail_after=None):
        self.speaker = FakeSpeaker(fail_after)


def install_pybricks_stubs():
    modules = {
        "pybricks": types.ModuleType("pybricks"),
        "pybricks.ev3devices": types.ModuleType("pybricks.ev3devices"),
        "pybricks.hubs": types.ModuleType("pybricks.hubs"),
        "pybricks.parameters": types.ModuleType("pybricks.parameters"),
    }
    modules["pybricks.ev3devices"].Motor = FakeMotor
    modules["pybricks.hubs"].EV3Brick = FakeBrick
    modules["pybricks.parameters"].Port = types.SimpleNamespace(
        S4="S4", A="A", B="B", D="D"
    )
    sys.modules.update(modules)


install_pybricks_stubs()
robot = importlib.import_module("dance")


class DanceTests(unittest.TestCase):
    def test_main_uses_configured_motor_ports(self):
        with patch.object(robot, "dance") as dance_program:
            robot.main()

        head_turn = dance_program.call_args.args[1]
        drive = dance_program.call_args.args[2]
        self.assertEqual(head_turn.port, robot.HEAD_TURN_MOTOR_PORT)
        self.assertEqual(drive.port, robot.DRIVE_MOTOR_PORT)

    def test_dance_plays_music_and_alternates_head_and_body(self):
        brick = FakeBrick()
        head_turn = FakeMotor()
        drive = FakeMotor()

        robot.dance(brick, head_turn, drive)

        self.assertEqual(
            brick.speaker.tones,
            list(robot.MELODY) * robot.DANCE_REPEATS,
        )
        moving_targets = [
            command[2]
            for command in head_turn.commands
            if command[0] == "run_target" and command[2] != 0
        ]
        self.assertEqual(
            moving_targets[:4],
            [-robot.HEAD_TURN_ANGLE, robot.HEAD_TURN_ANGLE] * 2,
        )
        self.assertIn(("run", -robot.BODY_DANCE_SPEED), drive.commands)
        self.assertIn(("run", robot.BODY_DANCE_SPEED), drive.commands)
        self.assertIn(
            ("run_target", robot.HEAD_TURN_SPEED, 0, True),
            head_turn.commands,
        )
        self.assertEqual(drive.commands[-1], ("brake",))
        self.assertEqual(head_turn.commands[-1], ("brake",))

    def test_dance_brakes_both_motors_if_playback_fails(self):
        brick = FakeBrick(fail_after=2)
        head_turn = FakeMotor()
        drive = FakeMotor()

        with self.assertRaises(RuntimeError):
            robot.dance(brick, head_turn, drive)

        self.assertEqual(drive.commands[-1], ("brake",))
        self.assertEqual(head_turn.commands[-1], ("brake",))


if __name__ == "__main__":
    unittest.main()
