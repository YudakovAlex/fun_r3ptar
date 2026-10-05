"""The 48-count Floor Demolition routine for Robodoz3r."""

from pybricks.parameters import Color, Stop

from config import BLADE_LIFT_ANGLE, DANCE_BEAT_TIME, TURN_SPEED


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

