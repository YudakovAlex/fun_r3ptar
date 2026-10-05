import importlib
import runpy
import sys
import types
import unittest
from unittest.mock import Mock, patch


class FakeMotor:
    def __init__(self, port=None, positive_direction=None):
        self.port = port
        self.angle_value = 0
        self.speed = 0
        self.remaining = None
        self.target = None
        self.jammed = False
        self.commands = []

    def angle(self):
        return self.angle_value

    def reset_angle(self, value):
        self.angle_value = value

    def run(self, speed):
        self.speed = speed
        self.remaining = None
        self.commands.append(("run", speed))

    def run_time(self, speed, duration, then, wait):
        self.run(speed)
        self.remaining = duration
        self.commands.append(("run_time", speed, duration, then, wait))

    def run_target(self, speed, target, then, wait):
        self.target = target
        self.speed = abs(speed) if target > self.angle_value else -abs(speed)
        self.commands.append(("run_target", speed, target, then, wait))

    def brake(self):
        self.speed = 0
        self.remaining = None
        self.target = None
        self.commands.append(("brake",))

    def tick(self, duration):
        if self.jammed:
            return
        elapsed = duration if self.remaining is None else min(duration, self.remaining)
        movement = self.speed * elapsed / 1000
        if self.target is not None and abs(self.target - self.angle_value) <= abs(movement):
            self.angle_value = self.target
            self.speed = 0
            self.target = None
        else:
            self.angle_value += movement
        if self.remaining is not None:
            self.remaining -= elapsed
            if self.remaining == 0:
                self.speed = 0


modules = {
    name: types.ModuleType(name)
    for name in (
        "pybricks", "pybricks.ev3devices", "pybricks.hubs",
        "pybricks.parameters", "pybricks.tools",
    )
}
modules["pybricks.ev3devices"].Motor = FakeMotor
modules["pybricks.ev3devices"].InfraredSensor = Mock
modules["pybricks.hubs"].EV3Brick = Mock
parameters = modules["pybricks.parameters"]
parameters.Port = types.SimpleNamespace(A="A", B="B", C="C", S4="S4")
parameters.Direction = types.SimpleNamespace(CLOCKWISE=1, COUNTERCLOCKWISE=-1)
parameters.Stop = types.SimpleNamespace(BRAKE="brake")
parameters.Color = types.SimpleNamespace(GREEN="green", ORANGE="orange")
parameters.Button = types.SimpleNamespace(CENTER="center")
modules["pybricks.tools"].StopWatch = Mock
modules["pybricks.tools"].wait = Mock

with patch.dict(sys.modules, modules):
    robot = importlib.import_module("main")


class DozerTests(unittest.TestCase):
    def setUp(self):
        self.brick = Mock()
        self.sensor = Mock()
        self.sensor.distance.return_value = 100
        self.left, self.right, self.blade = FakeMotor(), FakeMotor(), FakeMotor()
        self.motors = (self.left, self.right, self.blade)
        self.behavior = robot.DozerBehavior(
            self.brick, self.sensor, self.left, self.right, self.blade
        )
        self.now = 0
        self.behavior.start(self.now)

    def advance(self, duration):
        for unused in range(duration // robot.LOOP_DELAY):
            self.now += robot.LOOP_DELAY
            for motor in self.motors:
                motor.tick(robot.LOOP_DELAY)
            self.behavior.step(self.now)

    def cruise(self):
        self.advance(robot.GREETING_TIME * 2)
        self.assertEqual(self.behavior.state, robot.CRUISING)

    def test_greeting_salutes_then_lowers_before_driving(self):
        self.advance(robot.GREETING_TIME)
        self.assertEqual((self.left.speed, self.right.speed), (0, 0))
        self.advance(robot.GREETING_TIME)
        targets = [c[2] for c in self.blade.commands if c[0] == "run_target"]
        self.assertEqual(targets, [robot.BLADE_LIFT_ANGLE, 0])
        self.assertEqual(self.blade.angle(), 0)
        self.assertEqual((self.left.speed, self.right.speed), (robot.DRIVE_SPEED,) * 2)

    def test_obstacle_interrupts_cruise_and_reverses(self):
        self.cruise()
        self.sensor.distance.return_value = 55
        self.advance(robot.LOOP_DELAY)
        self.assertEqual(self.behavior.state, robot.BACKING)
        self.assertLess(self.left.speed, 0)
        self.assertLess(self.right.speed, 0)
        self.assertEqual(self.blade.target, robot.BLADE_LIFT_ANGLE)

    def test_path_above_obstacle_threshold_keeps_cruising(self):
        self.cruise()
        self.sensor.distance.return_value = 56
        self.advance(robot.LOOP_DELAY)
        self.assertEqual(self.behavior.state, robot.CRUISING)
        self.assertEqual((self.left.speed, self.right.speed), (robot.DRIVE_SPEED,) * 2)

    def test_obstacle_at_new_threshold_prevents_starting_forward(self):
        self.sensor.distance.return_value = 55
        self.advance(robot.GREETING_TIME * 2)
        self.assertEqual(self.behavior.state, robot.BACKING)
        for motor in (self.left, self.right):
            self.assertNotIn(("run", robot.DRIVE_SPEED), motor.commands)

    def test_backup_beeps_turns_then_resumes_on_clear_path(self):
        self.cruise()
        self.sensor.distance.return_value = 10
        self.advance(robot.LOOP_DELAY)
        self.brick.speaker.beep.reset_mock()
        self.advance(robot.BACKUP_TIME)
        self.assertGreaterEqual(self.brick.speaker.beep.call_count, 2)
        self.assertEqual(self.behavior.state, robot.TURNING)
        self.assertLess(self.left.speed * self.right.speed, 0)
        self.sensor.distance.return_value = 100
        self.advance(robot.TURN_TIME)
        self.assertEqual(self.behavior.state, robot.CRUISING)

    def test_persistent_obstacle_never_gets_forward_power(self):
        self.sensor.distance.return_value = 5
        self.advance(12000)
        for motor in (self.left, self.right):
            self.assertNotIn(("run", robot.DRIVE_SPEED), motor.commands)
        self.assertEqual(self.behavior.escape_attempts, 3)
        turns = [c[2] for c in self.left.commands if c[0] == "run_time" and c[2] >= robot.TURN_TIME]
        self.assertIn(robot.TURN_TIME + 600, turns)

    def test_periodic_dance_performs_six_sections_and_returns_to_work(self):
        self.cruise()
        self.behavior.next_dance = self.now
        self.brick.speaker.beep.reset_mock()
        self.brick.screen.print.reset_mock()
        self.left.commands.clear()
        self.right.commands.clear()
        self.blade.commands.clear()
        self.advance(robot.LOOP_DELAY + 48 * robot.dance.DANCE_BEAT_TIME)
        self.assertEqual(self.behavior.state, robot.CRUISING)
        notes = [call.args[0] for call in self.brick.speaker.beep.call_args_list]
        self.assertEqual(notes, [523, 659, 784, 1047] * 12)
        messages = [call.args[0] for call in self.brick.screen.print.call_args_list]
        for section in ("BOOT UP", "BULLDOZER SHUFFLE", "GEAR SHIFT",
                        "HYDRAULIC WAVE", "DEMOLITION MODE", "SYSTEM SHUTDOWN"):
            self.assertEqual(messages.count(section), 8)
        left_steps = [c[1] for c in self.left.commands if c[0] == "run_time"]
        right_steps = [c[1] for c in self.right.commands if c[0] == "run_time"]
        self.assertIn((robot.TURN_SPEED, robot.TURN_SPEED), list(zip(left_steps, right_steps)))
        self.assertIn((-robot.TURN_SPEED, -robot.TURN_SPEED), list(zip(left_steps, right_steps)))
        self.assertIn((robot.TURN_SPEED, -robot.TURN_SPEED), list(zip(left_steps, right_steps)))
        targets = [c[2] for c in self.blade.commands if c[0] == "run_target"]
        self.assertIn(robot.BLADE_LIFT_ANGLE // 4, targets)
        self.assertIn(robot.BLADE_LIFT_ANGLE * 3 // 4, targets)
        self.assertEqual(targets[-1], 0)
        self.assertEqual(self.blade.angle(), 0)
        self.assertGreater(self.behavior.next_dance, self.now)

    def test_obstacle_interrupts_dance(self):
        self.cruise()
        self.behavior.next_dance = self.now
        self.advance(robot.LOOP_DELAY)
        self.assertEqual(self.behavior.state, robot.DANCING)
        self.sensor.distance.return_value = 55
        self.advance(robot.LOOP_DELAY)
        self.assertEqual(self.behavior.state, robot.BACKING)
        self.assertLess(self.left.speed, 0)
        self.assertLess(self.right.speed, 0)

    def test_dance_freeze_brakes_tracks_and_stop_brakes_all_motors(self):
        self.cruise()
        self.behavior.next_dance = self.now
        self.advance(robot.LOOP_DELAY + 7 * robot.dance.DANCE_BEAT_TIME)
        self.assertEqual(self.behavior.state, robot.DANCING)
        self.assertEqual((self.left.speed, self.right.speed), (0, 0))
        self.advance(robot.dance.DANCE_BEAT_TIME)
        self.assertGreater(self.left.speed, 0)
        self.behavior.stop()
        self.assertTrue(all(motor.speed == 0 for motor in self.motors))

    def test_jammed_motors_do_not_stop_or_trigger_reverse(self):
        for motor in self.motors:
            motor.jammed = True
        self.advance(robot.GREETING_TIME * 2)
        self.assertEqual(self.behavior.state, robot.CRUISING)
        self.advance(4000)
        self.assertEqual(self.behavior.state, robot.CRUISING)
        self.assertEqual((self.left.speed, self.right.speed), (robot.DRIVE_SPEED,) * 2)
        self.assertEqual(self.blade.speed, 0)

    def run_standalone_dance(self):
        self.now = 0

        def tick(duration):
            self.now += duration
            for motor in self.motors:
                motor.tick(duration)

        with (
            patch.dict(sys.modules, {"main": robot}),
            patch.object(robot.dance, "EV3Brick", return_value=self.brick),
            patch.object(robot.dance, "InfraredSensor", return_value=self.sensor),
            patch.object(robot.dance, "Motor", side_effect=self.motors) as motor_type,
            patch.object(robot.dance, "StopWatch") as timer,
            patch.object(robot.dance, "wait", side_effect=tick),
        ):
            timer.return_value.time.side_effect = lambda: self.now
            robot.dance.main()
        return motor_type.call_args_list

    def test_dance_file_runs_as_a_program(self):
        self.sensor.distance.return_value = 55
        self.brick.buttons.pressed.return_value = []
        with (
            patch.dict(sys.modules, dict(modules, main=robot)),
            patch.object(modules["pybricks.hubs"], "EV3Brick", return_value=self.brick),
            patch.object(modules["pybricks.ev3devices"], "InfraredSensor", return_value=self.sensor),
            patch.object(modules["pybricks.ev3devices"], "Motor", side_effect=self.motors),
        ):
            runpy.run_path(robot.dance.__file__, run_name="__main__")
        self.assertTrue(all(motor.commands[-1] == ("brake",) for motor in self.motors))

    def test_standalone_dance_finishes_once_and_brakes(self):
        self.brick.speaker.beep.reset_mock()
        self.brick.screen.print.reset_mock()
        self.brick.buttons.pressed.side_effect = lambda: (
            [robot.Button.CENTER] if self.now < 100 else []
        )
        wiring = self.run_standalone_dance()
        self.assertEqual([call.args[0] for call in wiring], ["C", "B", "A"])
        self.assertEqual(
            [call.kwargs["positive_direction"] for call in wiring],
            [parameters.Direction.COUNTERCLOCKWISE,
             parameters.Direction.COUNTERCLOCKWISE, parameters.Direction.CLOCKWISE],
        )
        self.assertEqual(self.brick.speaker.beep.call_count, 48)
        messages = [call.args[0] for call in self.brick.screen.print.call_args_list]
        for section, unused in robot.dance.DANCE_ROUTINE:
            self.assertEqual(messages.count(section), 8)
        self.assertEqual(self.now, 48 * robot.dance.DANCE_BEAT_TIME)
        self.assertEqual(self.blade.angle(), 0)
        self.assertTrue(all(motor.commands[-1] == ("brake",) for motor in self.motors))

    def test_standalone_dance_stops_on_button_obstacle_or_failure(self):
        for reason in ("button", "obstacle", "speaker", "sensor"):
            with self.subTest(reason=reason):
                self.brick.speaker.beep.reset_mock()
                self.brick.speaker.beep.side_effect = (
                    RuntimeError("speaker") if reason == "speaker" else None
                )
                self.brick.buttons.pressed.side_effect = lambda: (
                    [robot.Button.CENTER] if reason == "button" and self.now >= 100 else []
                )
                self.sensor.distance.side_effect = (
                    OSError("sensor") if reason == "sensor" else
                    lambda: 55 if reason == "obstacle" and self.now >= 100 else 100
                )
                if reason in ("speaker", "sensor"):
                    with self.assertRaisesRegex((RuntimeError, OSError), reason):
                        self.run_standalone_dance()
                else:
                    self.run_standalone_dance()
                    self.assertEqual(self.now, 100)
                    self.assertEqual(self.brick.speaker.beep.call_count, 1)
                self.assertTrue(all(motor.commands[-1] == ("brake",) for motor in self.motors))

    def test_main_wiring_and_center_button_shutdown(self):
        self.brick.buttons.pressed.side_effect = [[], [robot.Button.CENTER]]
        with (
            patch.object(robot, "EV3Brick", return_value=self.brick),
            patch.object(robot, "InfraredSensor") as sensor_type,
            patch.object(robot, "Motor", side_effect=self.motors) as motor_type,
            patch.object(robot, "StopWatch") as timer,
        ):
            timer.return_value.time.return_value = 0
            robot.main()
        sensor_type.assert_called_once_with(robot.INFRARED_SENSOR_PORT)
        self.assertEqual([call.args[0] for call in motor_type.call_args_list], ["C", "B", "A"])
        self.assertEqual(
            [call.kwargs["positive_direction"] for call in motor_type.call_args_list],
            [parameters.Direction.COUNTERCLOCKWISE,
             parameters.Direction.COUNTERCLOCKWISE, parameters.Direction.CLOCKWISE],
        )
        self.assertTrue(all(motor.commands[-1] == ("brake",) for motor in self.motors))

    def test_main_ignores_launch_press_and_runs_until_a_new_press(self):
        now = 0
        states = set()

        def buttons():
            if now < robot.GREETING_TIME or now >= 60000:
                return [robot.Button.CENTER]
            return []

        def tick(duration):
            nonlocal now
            now += duration
            for motor in self.motors:
                motor.tick(duration)

        original_step = robot.DozerBehavior.step

        def step(behavior, time):
            original_step(behavior, time)
            states.add(behavior.state)

        self.brick.buttons.pressed.side_effect = buttons
        with (
            patch.object(robot, "EV3Brick", return_value=self.brick),
            patch.object(robot, "InfraredSensor", return_value=self.sensor),
            patch.object(robot, "Motor", side_effect=self.motors),
            patch.object(robot, "StopWatch") as timer,
            patch.object(robot, "wait", side_effect=tick),
            patch.object(robot.DozerBehavior, "step", step),
        ):
            timer.return_value.time.side_effect = lambda: now
            robot.main()

        self.assertEqual(now, 60000)
        self.assertTrue({robot.GREETING, robot.LOWERING, robot.CRUISING, robot.DANCING} <= states)
        self.assertTrue(all(motor.commands[-1] == ("brake",) for motor in self.motors))

    def test_main_brakes_on_startup_sensor_and_loop_failures(self):
        for failure in ("startup", "sensor", "interrupt"):
            with self.subTest(failure=failure):
                self.brick.buttons.pressed.return_value = []
                with (
                    patch.object(robot, "EV3Brick", return_value=self.brick),
                    patch.object(robot, "InfraredSensor", return_value=self.sensor),
                    patch.object(robot, "Motor", side_effect=self.motors),
                    patch.object(robot, "StopWatch") as timer,
                    patch.object(robot, "wait") as wait,
                ):
                    timer.return_value.time.side_effect = [0, 800, 1600]
                    self.brick.speaker.beep.side_effect = RuntimeError("speaker") if failure == "startup" else None
                    self.sensor.distance.side_effect = OSError("sensor") if failure == "sensor" else None
                    wait.side_effect = KeyboardInterrupt if failure == "interrupt" else None
                    # Model a blade that reaches each target during this main-loop test.
                    with patch.object(self.blade, "angle", side_effect=lambda: self.blade.target or 0):
                        with self.assertRaises((RuntimeError, OSError, KeyboardInterrupt)):
                            robot.main()
                self.assertTrue(all(motor.commands[-1] == ("brake",) for motor in self.motors))


if __name__ == "__main__":
    unittest.main()
