import math
import time


def _now_ms() -> float:
    return time.monotonic() * 1000.0


def approach(cur: float, tgt: float, max_delta: float) -> float:
    d = tgt - cur
    if abs(d) <= max_delta:
        return tgt
    return cur + math.copysign(max_delta, d)


SMOOTH_SPEED = 360.0  # dg/s


class FixtureState:
    """Smoothed servo angles + LED flicker/fade, ported from the pygame sim."""

    def __init__(self):
        self.base_current = self.base_target = 90.0
        self.head_current = self.head_target = 90.0
        self.led_color = (1.0, 1.0, 1.0)
        self.flicker_end = 0.0
        self.flicker_color = (1.0, 1.0, 1.0)
        self.fade_active = False
        self.fade_start_color = (1.0, 1.0, 1.0)
        self.fade_end_color = (1.0, 1.0, 1.0)
        self.fade_start = 0.0
        self.fade_duration = 0

    def apply(self, cmd: dict):
        if "servo" in cmd:
            items = cmd["servo"] if isinstance(cmd["servo"], list) else [cmd]
            for item in items:
                name, ang = item.get("servo"), item.get("angle")
                if ang is None:
                    continue
                if name == "base":
                    self.base_target = float(ang)
                elif name == "top":
                    self.head_target = float(ang)

        led = cmd.get("led")
        if isinstance(led, dict):
            r, g, b = (led.get(c, 0) / 255.0 for c in "rgb")
            now = _now_ms()
            if "flicker" in cmd:
                self.flicker_end = now + int(cmd["flicker"])
                self.flicker_color = (r, g, b)
                self.fade_active = False
            elif "fade" in cmd:
                fr, fg, fb = self.led_color
                src = cmd.get("from")
                if isinstance(src, dict):
                    fr = src.get("r", fr * 255) / 255.0
                    fg = src.get("g", fg * 255) / 255.0
                    fb = src.get("b", fb * 255) / 255.0
                self.fade_active = True
                self.fade_start_color = (fr, fg, fb)
                self.fade_end_color = (r, g, b)
                self.fade_start = now
                self.fade_duration = int(cmd["fade"])
                self.flicker_end = 0.0
            else:
                self.led_color = (r, g, b)
                self.flicker_end = 0.0
                self.fade_active = False

    def update(self, dt: float):
        """Advance servos and compute this frame's colour. Returns (base, head, (r,g,b))."""
        step = SMOOTH_SPEED * dt
        self.base_current = approach(self.base_current, self.base_target, step)
        self.head_current = approach(self.head_current, self.head_target, step)

        now = _now_ms()
        color = self.led_color
        if now < self.flicker_end:
            color = self.flicker_color if int(now // 50) % 2 == 0 else (0.0, 0.0, 0.0)
        elif self.fade_active:
            t = now - self.fade_start
            if t >= self.fade_duration:
                color = self.fade_end_color
                self.fade_active = False
            else:
                f = (t / self.fade_duration) ** 4 if self.fade_duration > 0 else 1.0
                sc, ec = self.fade_start_color, self.fade_end_color
                color = tuple(sc[i] + (ec[i] - sc[i]) * f for i in range(3))
        self.led_color = color
        return self.base_current, self.head_current, color
