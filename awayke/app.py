"""Awayke for Linux: tray app. Port of AppDelegate.swift."""
import json
import os
import signal
import subprocess
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import AyatanaAppIndicator3 as AppIndicator  # noqa: E402
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from . import policy  # noqa: E402
from .system import (BatteryMonitor, DisplayWakeKeeper, LidMonitor,  # noqa: E402
                     SleepInhibitor, notify)

APP_ID = "io.github.daemonphantom.Awayke"
DATA_DIR = os.environ.get("AWAYKE_HOME", os.path.expanduser("~/.local/share/awayke"))
CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "awayke", "config.json")
THRESHOLDS = [0, 10, 20, 30]
DURATIONS = [15, 30, 60, 120]


def duration_label(m):
    if m < 60:
        return f"{m} minutes"
    h, r = divmod(m, 60)
    part = "1 hour" if h == 1 else f"{h} hours"
    return part if r == 0 else f"{part} {r} min"


def format_remaining(seconds):
    m = max(1, -(-int(seconds) // 60))
    if m < 60:
        return f"{m}m"
    h, r = divmod(m, 60)
    return f"{h}h" if r == 0 else f"{h}h {r}m"


class Awayke(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.inhibitor = SleepInhibitor()
        self.display = DisplayWakeKeeper()
        self.battery = BatteryMonitor()
        self.lid = LidMonitor()
        self.lid_session = policy.LidSessionTracker()
        self.intent = False
        self.suspended = False
        self.override = False
        self.last_snapshot = None
        self.deadline = None
        self.tick_id = None
        self.threshold = self._load_threshold()
        self.indicator = None
        self.state_item = None

    # ---- persistence -------------------------------------------------
    def _load_threshold(self):
        try:
            with open(CONFIG) as f:
                v = int(json.load(f).get("autoOffThreshold", 0))
            return v if v in THRESHOLDS else 0
        except (OSError, ValueError):
            return 0

    def _save_threshold(self):
        os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
        with open(CONFIG, "w") as f:
            json.dump({"autoOffThreshold": self.threshold}, f)

    # ---- lifecycle ---------------------------------------------------
    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()
        icons = os.path.join(DATA_DIR, "icons")
        self.indicator = AppIndicator.Indicator.new(
            "awayke", "awayke-off", AppIndicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_icon_theme_path(icons)
        no_tray = os.environ.get("AWAYKE_NO_TRAY") == "1"
        self.indicator.set_status(AppIndicator.IndicatorStatus.PASSIVE if no_tray
                                  else AppIndicator.IndicatorStatus.ACTIVE)
        self.indicator.set_title("Awayke")

        self.battery.on_change = self.handle_battery
        if not self.battery.start():
            print("Awayke: UPower unavailable; battery auto-off disabled.", file=sys.stderr)
        self.lid.on_change = self.handle_lid
        if not self.lid.start():
            print("Awayke: lid monitoring unavailable; until-lid-reopens sessions cannot end on their own.",
                  file=sys.stderr)

        # Exported on the session bus at /io/github/daemonphantom/Awayke; the GNOME
        # Quick Settings extension drives the app through these.
        self.act_active = Gio.SimpleAction.new_stateful("active", None, GLib.Variant.new_boolean(False))
        self.act_active.connect("activate", lambda *_: self.set_intent(not self.effective_active))
        self.add_action(self.act_active)
        self.act_status = Gio.SimpleAction.new_stateful("status", None, GLib.Variant.new_string("Inactive"))
        self.act_status.set_enabled(False)
        self.add_action(self.act_status)
        self.act_auto = Gio.SimpleAction.new_stateful("auto-off", GLib.VariantType.new("i"),
                                                      GLib.Variant.new_int32(self.threshold))
        self.act_auto.connect("activate", lambda a, p: self.menu_set_threshold(p.get_int32())
                              if p.get_int32() in THRESHOLDS else None)
        self.add_action(self.act_auto)
        keep = Gio.SimpleAction.new("keep-for", GLib.VariantType.new("i"))
        keep.connect("activate", self._on_keep_for)
        self.add_action(keep)

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._on_signal)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._on_signal)
        self.refresh()

    def _on_keep_for(self, action, param):
        minutes = param.get_int32()
        if minutes < 0:
            self.menu_until_lid()
        else:
            self.menu_keep_for(minutes)

    def do_activate(self):
        pass

    def do_shutdown(self):
        self.inhibitor.release()
        self.display.allow()
        Gtk.Application.do_shutdown(self)

    def _on_signal(self):
        self.quit_app()
        return False

    def quit_app(self):
        self.inhibitor.release()
        self.display.allow()
        self.quit()

    # ---- state -------------------------------------------------------
    @property
    def effective_active(self):
        return self.intent and not self.suspended

    @property
    def remaining(self):
        return None if self.deadline is None else max(0, self.deadline - time.monotonic())

    @property
    def below_floor(self):
        if self.threshold <= 0 or not self.last_snapshot:
            return False
        pct, ac = self.last_snapshot
        return not ac and pct < self.threshold

    def _apply(self, disable):
        try:
            if disable:
                self.inhibitor.acquire()
            else:
                self.inhibitor.release()
            return True
        except Exception as e:
            self.present_error(e)
            return False

    def set_intent(self, on, timer_minutes=None, until_lid=False):
        if not self._apply(on):
            return
        self.intent = on
        self.suspended = False
        self.override = on and self.below_floor
        if on and until_lid:
            self.cancel_timer()
            self.lid_session.start(self.lid.is_closed)
        elif on and timer_minutes:
            self.lid_session.cancel()
            self.start_timer(timer_minutes)
        else:
            self.cancel_timer()
            self.lid_session.cancel()
        self.sync_display()
        self.refresh()

    def start_timer(self, minutes):
        self.cancel_timer()
        self.deadline = time.monotonic() + minutes * 60
        self.tick_id = GLib.timeout_add_seconds(15, self._tick)

    def cancel_timer(self):
        if self.tick_id:
            GLib.source_remove(self.tick_id)
            self.tick_id = None
        self.deadline = None

    def _tick(self):
        if self.deadline is None:
            return False
        if time.monotonic() >= self.deadline:
            self.tick_id = None
            self.cancel_timer()
            self.end_session("Timer finished.")
            return False
        self.refresh()
        return True

    def end_session(self, body):
        self.cancel_timer()
        self.lid_session.cancel()
        if not self.intent:
            return
        if not self.suspended and not self._apply(False):
            if body == "The lid was reopened.":
                self.lid_session.start(self.lid.is_closed)
            self.refresh()
            return
        self.intent = False
        self.suspended = False
        self.override = False
        self.sync_display()
        self.refresh()
        notify("Awayke turned off", body)

    def sync_display(self):
        (self.display.prevent if self.effective_active else self.display.allow)()

    def handle_lid(self, closed):
        if self.lid_session.handle(closed):
            self.end_session("The lid was reopened.")

    def handle_battery(self, percent, on_ac):
        self.last_snapshot = (percent, on_ac)
        self.override = policy.should_keep_override(self.override, on_ac)
        action = policy.decide(self.intent, self.suspended, percent, on_ac, self.threshold, self.override)
        if action == policy.NONE:
            return
        suspending = action == policy.SUSPEND
        if not self._apply(not suspending):
            return
        self.suspended = suspending
        self.sync_display()
        self.refresh()
        if suspending:
            notify("Awayke turned off", f"Battery dropped below {self.threshold}%.")
        else:
            notify("Awayke back on", "Charging - sleep prevention resumed.")

    # ---- UI ----------------------------------------------------------
    def state_title(self):
        if self.suspended:
            return "Paused (low battery)"
        if self.effective_active and self.lid_session.is_active:
            return ("Active - waiting for lid to close" if self.lid_session.is_waiting_for_close
                    else "Active - until lid reopens")
        if self.effective_active and self.remaining is not None:
            return f"Active - {format_remaining(self.remaining)} left"
        return "Active" if self.effective_active else "Inactive"

    def refresh(self):
        self.act_active.set_state(GLib.Variant.new_boolean(self.effective_active))
        self.act_auto.set_state(GLib.Variant.new_int32(self.threshold))
        self.act_status.set_state(GLib.Variant.new_string(self.state_title()))
        self.indicator.set_icon_full("awayke-on" if self.effective_active else "awayke-off", self.state_title())
        self.indicator.set_secondary_activate_target(None)
        self.indicator.set_menu(self.build_menu())
        self.indicator.set_secondary_activate_target(self.toggle_item)

    def build_menu(self):
        menu = Gtk.Menu()

        def add(label, cb=None, parent=menu, check=None, sensitive=True):
            item = Gtk.CheckMenuItem(label=label) if check is not None else Gtk.MenuItem(label=label)
            if check is not None:
                item.set_draw_as_radio(True)
                item.set_active(check)
            item.set_sensitive(sensitive)
            if cb:
                item.connect("activate", cb)
            parent.append(item)
            return item

        add(self.state_title(), sensitive=False)
        toggle = add("Turn Off" if self.effective_active else "Turn On",
                     lambda _: self.set_intent(not self.effective_active))
        self.toggle_item = toggle
        menu.append(Gtk.SeparatorMenuItem())

        keep = Gtk.MenuItem(label="Keep awayke for")
        sub = Gtk.Menu()
        add("Until lid is reopened", lambda _: self.menu_until_lid(), sub,
            check=self.effective_active and self.lid_session.is_active)
        sub.append(Gtk.SeparatorMenuItem())
        for m in DURATIONS:
            add(duration_label(m), lambda _, m=m: self.menu_keep_for(m), sub)
        sub.append(Gtk.SeparatorMenuItem())
        add("Indefinitely", lambda _: self.menu_keep_for(0), sub,
            check=self.effective_active and self.deadline is None and not self.lid_session.is_active)
        keep.set_submenu(sub)
        menu.append(keep)

        auto = Gtk.MenuItem(label="Auto-off on low battery")
        sub = Gtk.Menu()
        for v in THRESHOLDS:
            add("Off" if v == 0 else f"At {v}%", lambda _, v=v: self.menu_set_threshold(v), sub,
                check=(v == self.threshold), sensitive=self.last_snapshot is not None or v == self.threshold or v == 0)
        auto.set_submenu(sub)
        menu.append(auto)

        menu.append(Gtk.SeparatorMenuItem())
        add("Uninstall Awayke…", lambda _: self.menu_uninstall())
        menu.append(Gtk.SeparatorMenuItem())
        add("Quit Awayke", lambda _: self.quit_app())
        menu.show_all()
        return menu

    def menu_keep_for(self, minutes):
        if not self.effective_active:
            self.set_intent(True, timer_minutes=minutes or None)
            return
        self.lid_session.cancel()
        if minutes:
            self.start_timer(minutes)
        else:
            self.cancel_timer()
        self.refresh()

    def menu_until_lid(self):
        if not self.effective_active:
            self.set_intent(True, until_lid=True)
            return
        self.cancel_timer()
        self.lid_session.start(self.lid.is_closed)
        self.refresh()

    def menu_set_threshold(self, value):
        self.threshold = value
        self._save_threshold()
        if self.last_snapshot:
            self.handle_battery(*self.last_snapshot)
        self.refresh()

    def menu_uninstall(self):
        dlg = Gtk.MessageDialog(message_type=Gtk.MessageType.WARNING, text="Uninstall Awayke?",
                                secondary_text="This removes Awayke's files and autostart entry, then quits.")
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Uninstall", Gtk.ResponseType.OK)
        ok = dlg.run() == Gtk.ResponseType.OK
        dlg.destroy()
        script = os.path.join(DATA_DIR, "uninstall.sh")
        if ok and os.path.exists(script):
            subprocess.Popen(["/bin/sh", script], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.quit_app()

    def present_error(self, error):
        notify("Awayke couldn't toggle sleep.", str(error))
        print(f"Awayke: {error}", file=sys.stderr)


def main():
    return Awayke().run(None)
