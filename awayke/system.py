"""Linux system integration: logind inhibitor, UPower lid/battery, notifications."""
import glob
import os
import subprocess
import time

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

LOGIND = ("org.freedesktop.login1", "/org/freedesktop/login1", "org.freedesktop.login1.Manager")
UPOWER = "org.freedesktop.UPower"
UPOWER_PATH = "/org/freedesktop/UPower"
UPOWER_DISPLAY = "/org/freedesktop/UPower/devices/DisplayDevice"
INHIBIT_WHAT = "handle-lid-switch:sleep:idle"


class SleepInhibitor:
    """Holds a logind block inhibitor. Closing the fd releases it, and the
    kernel closes it if the process dies, so a crash can never leave the
    machine unable to sleep."""

    def __init__(self):
        self._fd = None
        self._proc = None

    @property
    def held(self):
        return self._fd is not None or self._proc is not None

    def acquire(self):
        if self.held:
            return
        try:
            self._acquire_dbus()
        except Exception as dbus_error:
            self._acquire_subprocess(dbus_error)

    def _acquire_dbus(self):
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        reply, fds = bus.call_with_unix_fd_list_sync(
            LOGIND[0], LOGIND[1], LOGIND[2], "Inhibit",
            GLib.Variant("(ssss)", (INHIBIT_WHAT, "Awayke", "Awayke is keeping this machine awake", "block")),
            GLib.VariantType("(h)"), Gio.DBusCallFlags.NONE, 5000, None, None)
        self._fd = fds.steal_fds()[reply.unpack()[0]]

    def _acquire_subprocess(self, original):
        try:
            proc = subprocess.Popen(
                ["systemd-inhibit", f"--what={INHIBIT_WHAT}", "--who=Awayke",
                 "--why=Awayke is keeping this machine awake", "--mode=block", "sleep", "infinity"],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            time.sleep(0.3)
            if proc.poll() is not None:
                raise RuntimeError(proc.stderr.read().decode().strip() or "systemd-inhibit exited")
            self._proc = proc
        except Exception as e:
            raise RuntimeError(f"Could not acquire logind inhibitor: {original}; fallback: {e}")

    def release(self):
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None
        if self._proc is not None:
            self._proc.terminate()
            self._proc.wait()
            self._proc = None


class DisplayWakeKeeper:
    """Stops screen blank / auto-lock via the GNOME session inhibitor (best effort)."""

    def __init__(self):
        self._cookie = None

    def prevent(self):
        if self._cookie is not None:
            return
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            r = bus.call_sync(
                "org.gnome.SessionManager", "/org/gnome/SessionManager", "org.gnome.SessionManager",
                "Inhibit", GLib.Variant("(susu)", ("Awayke", 0, "Awayke is active", 8)),
                GLib.VariantType("(u)"), Gio.DBusCallFlags.NONE, 2000, None)
            self._cookie = r.unpack()[0]
        except Exception:
            self._cookie = None

    def allow(self):
        if self._cookie is None:
            return
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
                "org.gnome.SessionManager", "/org/gnome/SessionManager", "org.gnome.SessionManager",
                "Uninhibit", GLib.Variant("(u)", (self._cookie,)), None, Gio.DBusCallFlags.NONE, 2000, None)
        except Exception:
            pass
        self._cookie = None


class LidMonitor:
    """UPower LidIsClosed, with /proc/acpi polling as a fallback."""

    def __init__(self):
        self.on_change = None
        self.is_closed = None
        self._proxy = None
        self._poll_id = None

    def start(self):
        try:
            self._proxy = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None,
                UPOWER, UPOWER_PATH, "org.freedesktop.UPower", None)
            if self._proxy.get_cached_property("LidIsPresent") is not None \
                    and self._proxy.get_cached_property("LidIsClosed") is not None:
                self._proxy.connect("g-properties-changed", self._on_props)
                self._emit(self._proxy.get_cached_property("LidIsClosed").get_boolean())
                return True
        except Exception:
            pass
        self._proxy = None
        if self._read_proc() is None:
            return False
        self._emit(self._read_proc())
        self._poll_id = GLib.timeout_add_seconds(2, self._poll)
        return True

    def stop(self):
        if self._poll_id:
            GLib.source_remove(self._poll_id)
            self._poll_id = None
        self._proxy = None
        self.is_closed = None

    def _on_props(self, proxy, changed, invalidated):
        value = changed.lookup_value("LidIsClosed", None)
        if value is not None:
            self._emit(value.get_boolean())

    def _poll(self):
        state = self._read_proc()
        if state is not None:
            self._emit(state)
        return True

    @staticmethod
    def _read_proc():
        for path in glob.glob("/proc/acpi/button/lid/*/state"):
            try:
                with open(path) as f:
                    return "closed" in f.read()
            except OSError:
                continue
        return None

    def _emit(self, closed):
        if closed == self.is_closed:
            return
        self.is_closed = closed
        if self.on_change:
            self.on_change(closed)


class BatteryMonitor:
    """UPower DisplayDevice. Machines without a battery never emit."""

    def __init__(self):
        self.on_change = None
        self._root = None
        self._dev = None

    def start(self):
        try:
            self._root = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None,
                UPOWER, UPOWER_PATH, "org.freedesktop.UPower", None)
            self._dev = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None,
                UPOWER, UPOWER_DISPLAY, "org.freedesktop.UPower.Device", None)
        except Exception:
            return False
        self._root.connect("g-properties-changed", lambda *a: self._emit())
        self._dev.connect("g-properties-changed", lambda *a: self._emit())
        self._emit()
        return True

    def snapshot(self):
        if not self._dev or not self._root:
            return None
        present = self._dev.get_cached_property("IsPresent")
        pct = self._dev.get_cached_property("Percentage")
        on_batt = self._root.get_cached_property("OnBattery")
        if present is None or not present.get_boolean() or pct is None or on_batt is None:
            return None
        return int(pct.get_double()), not on_batt.get_boolean()

    def _emit(self):
        snap = self.snapshot()
        if snap and self.on_change:
            self.on_change(*snap)


def notify(title, body):
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call_sync(
            "org.freedesktop.Notifications", "/org/freedesktop/Notifications",
            "org.freedesktop.Notifications", "Notify",
            GLib.Variant("(susssasa{sv}i)", ("Awayke", 0, "awayke-off", title, body, [], {}, 5000)),
            None, Gio.DBusCallFlags.NONE, 2000, None)
    except Exception:
        pass
