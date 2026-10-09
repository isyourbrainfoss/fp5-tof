#!/usr/bin/env python3
"""FP5 ToF live view — GTK4/Adwaita.

Streams millimetres from ``fp5-tof-live.sh`` (ST VL53L3CX ULD ranger).
Point the **rear** camera module at a wall. Does not touch NFC GPIO 38.
"""
from __future__ import annotations

import math
import os
import signal
import subprocess
import sys
from collections import deque
from pathlib import Path

for p in (
    os.path.dirname(os.path.abspath(__file__)),
    "/usr/local/lib/fp5-tof",
    "/usr/local/bin",
):
    if p not in sys.path:
        sys.path.insert(0, p)

from fp5_tof import parse_uld_sample  # noqa: E402

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

APP_ID = "org.fp5.tof"
MAX_MM = 3000.0
HISTORY = 80

STATUS_HINT = {
    0: "valid",
    1: "sigma",
    2: "signal",
    3: "min range",
    4: "phase",
    5: "hw fail",
    6: "wrap / settle",
    7: "wrap",
    255: "no target",
}

CSS = """
window { background-color: #0e1418; }
.mm {
  font-size: 64px;
  font-weight: 800;
  color: #e8f0f7;
  font-feature-settings: "tnum";
}
.unit { font-size: 18px; color: #8aa0b4; }
.ok { color: #4ade80; }
.warn { color: #fbbf24; }
.bad { color: #fca5a5; }
.meta { font-size: 14px; color: #9aadc0; }
.hint { font-size: 13px; color: #6b7c8d; }
"""


def live_script() -> Path:
    here = Path(__file__).resolve().parent
    for p in (
        here / "fp5-tof-live.sh",
        Path("/usr/local/bin/fp5-tof-live.sh"),
        Path("/usr/local/lib/fp5-tof/fp5-tof-live.sh"),
    ):
        if p.is_file():
            return p
    return here / "fp5-tof-live.sh"


def fmt_distance(mm: int | None) -> str:
    if mm is None:
        return "—"
    if mm < 1000:
        return f"{mm}"
    return f"{mm / 1000:.2f}".rstrip("0").rstrip(".")


def fmt_unit(mm: int | None) -> str:
    if mm is None:
        return ""
    if mm < 1000:
        return "mm"
    return "m"


class DepthView(Gtk.DrawingArea):
    def __init__(self) -> None:
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_content_width(320)
        self.set_content_height(280)
        self.history: deque[float] = deque(maxlen=HISTORY)
        self.mm: int | None = None
        self.valid = False
        self.set_draw_func(self._draw)

    def push(self, mm: int | None, valid: bool) -> None:
        self.mm = mm
        self.valid = valid
        if mm is not None and valid:
            self.history.append(float(mm))
        self.queue_draw()

    def _draw(self, _area, cr, width: int, height: int) -> None:
        cr.set_source_rgb(0.055, 0.078, 0.094)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        pad = 16.0
        w = width - 2 * pad
        h = height - 2 * pad
        if w <= 8 or h <= 8:
            return
        x0 = pad
        y0 = pad

        # Depth bar: near at bottom, far at top (sensor looking "out").
        cr.set_source_rgba(0.2, 0.28, 0.34, 1)
        cr.rectangle(x0, y0, 36, h)
        cr.fill()

        def y_for(mm: float) -> float:
            t = min(1.0, max(0.0, mm / MAX_MM))
            return y0 + h - t * h

        if self.mm is not None and self.valid:
            y = y_for(float(self.mm))
            cr.set_source_rgb(0.29, 0.87, 0.5)
            cr.rectangle(x0, y, 36, y0 + h - y)
            cr.fill()
            cr.arc(x0 + 18, y, 8, 0, 2 * math.pi)
            cr.fill()

        # Sparkline
        if len(self.history) >= 2:
            cr.set_source_rgb(0.45, 0.72, 0.95)
            cr.set_line_width(2.0)
            n = len(self.history)
            gx0 = x0 + 52
            gw = w - 52
            first = True
            for i, mm in enumerate(self.history):
                x = gx0 + (i / max(1, n - 1)) * gw
                y = y_for(mm)
                if first:
                    cr.move_to(x, y)
                    first = False
                else:
                    cr.line_to(x, y)
            cr.stroke()

        cr.set_source_rgb(0.42, 0.5, 0.58)
        cr.select_font_face("sans-serif")
        cr.set_font_size(11)
        cr.move_to(x0 + 44, y0 + 12)
        cr.show_text("3 m")
        cr.move_to(x0 + 44, y0 + h)
        cr.show_text("0")


class TofViewApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        self.win: Adw.ApplicationWindow | None = None
        self.mm_label: Gtk.Label | None = None
        self.unit_label: Gtk.Label | None = None
        self.meta: Gtk.Label | None = None
        self.hint: Gtk.Label | None = None
        self.depth: DepthView | None = None
        self.proc: subprocess.Popen | None = None
        self.channel = None
        self.last_valid: int | None = None
        self.samples = 0

    def do_activate(self) -> None:  # noqa: N802
        if self.win:
            self.win.present()
            return
        css = Gtk.CssProvider()
        css.load_from_data(CSS.encode())
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        self.win = Adw.ApplicationWindow(application=self, title="FP5 ToF")
        self.win.set_default_size(360, 640)
        self.win.connect("close-request", self._on_close)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.win.set_content(root)
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Time of flight"))
        root.append(header)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_margin_top(8)
        body.set_margin_start(16)
        body.set_margin_end(16)
        body.set_margin_bottom(12)
        body.set_vexpand(True)
        root.append(body)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_halign(Gtk.Align.CENTER)
        self.mm_label = Gtk.Label(label="—")
        self.mm_label.add_css_class("mm")
        self.unit_label = Gtk.Label(label="")
        self.unit_label.add_css_class("unit")
        self.unit_label.set_valign(Gtk.Align.END)
        self.unit_label.set_margin_bottom(12)
        row.append(self.mm_label)
        row.append(self.unit_label)
        body.append(row)

        self.meta = Gtk.Label(label="Starting ranger…")
        self.meta.add_css_class("meta")
        self.meta.set_wrap(True)
        body.append(self.meta)

        self.depth = DepthView()
        body.append(self.depth)

        self.hint = Gtk.Label(
            label="Point the rear camera island at a wall (not the screen). "
            "Cone is ~25°. NFC stays on GPIO 38.",
            wrap=True,
            justify=Gtk.Justification.CENTER,
        )
        self.hint.add_css_class("hint")
        self.hint.set_wrap(True)
        body.append(self.hint)

        self.win.present()
        GLib.idle_add(self._start_ranger)

    def _start_ranger(self) -> bool:
        script = live_script()
        cmd = ["sudo", "-n", str(script)]
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid,
            )
        except OSError as e:
            self._set_meta(f"Could not start ranger: {e}", "bad")
            return False
        if not self.proc.stdout:
            self._set_meta("Ranger has no stdout", "bad")
            return False
        GLib.io_add_watch(
            self.proc.stdout, GLib.IO_IN | GLib.IO_HUP, self._on_io
        )
        self._set_meta("Listening on i2c-9 0x29…", "meta")
        return False

    def _on_io(self, _src, cond) -> bool:
        if cond & GLib.IO_HUP and not (cond & GLib.IO_IN):
            self._set_meta("Ranger stopped", "warn")
            return False
        if not self.proc or not self.proc.stdout:
            return False
        line = self.proc.stdout.readline()
        if not line:
            return True
        sample = parse_uld_sample(line)
        if not sample:
            if "INIT_FAIL" in line or "START_FAIL" in line:
                self._set_meta(line.strip(), "bad")
            return True
        self.samples += 1
        mm = sample["mm"]
        valid = sample["valid"]
        if valid:
            self.last_valid = mm
        if self.mm_label:
            show = mm if valid else self.last_valid
            self.mm_label.set_text(fmt_distance(show if valid else mm))
            self.mm_label.remove_css_class("ok")
            self.mm_label.remove_css_class("warn")
            self.mm_label.remove_css_class("bad")
            self.mm_label.add_css_class("ok" if valid else "warn")
        if self.unit_label:
            self.unit_label.set_text(fmt_unit(mm))
        if self.depth:
            self.depth.push(mm if valid else None, valid)
        hint = STATUS_HINT.get(sample["status"], f"st={sample['status']}")
        extra = ""
        if valid and mm < 1000:
            extra = f"  ({mm / 10:.1f} cm)"
        elif valid:
            extra = f"  ({mm / 1000:.2f} m)"
        self._set_meta(
            f"{hint} · obj {sample['obj']} · n={self.samples}{extra}",
            "ok" if valid else "warn",
        )
        return True

    def _set_meta(self, text: str, kind: str = "meta") -> None:
        if not self.meta:
            return
        self.meta.set_text(text)
        for c in ("ok", "warn", "bad", "meta"):
            self.meta.remove_css_class(c)
        self.meta.add_css_class(kind)

    def _on_close(self, *_a) -> bool:
        self._stop()
        return False

    def do_shutdown(self) -> None:  # noqa: N802
        self._stop()
        Adw.Application.do_shutdown(self)

    def _stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError):
                self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
        subprocess.run(
            ["sudo", "-n", "rmmod", "tof-rail"],
            capture_output=True,
            timeout=5,
            check=False,
        )


def main() -> int:
    Adw.init()
    app = TofViewApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
