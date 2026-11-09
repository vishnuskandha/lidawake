"""Fake logind + UPower on a private bus (set DBUS_SYSTEM_BUS_ADDRESS). Test helper.
stdin commands: 'lid 0|1', 'batt <pct> <on_battery 0|1>'. Writes inhibitor count to $MOCK_STATE."""
import os
import sys
import threading

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

STATE = os.environ["MOCK_STATE"]
inhib = {}  # id -> (read_fd, what)
props = {
    "/org/freedesktop/UPower": {"LidIsPresent": GLib.Variant("b", True), "LidIsClosed": GLib.Variant("b", False),
                                "OnBattery": GLib.Variant("b", False)},
    "/org/freedesktop/UPower/devices/DisplayDevice": {"IsPresent": GLib.Variant("b", True),
                                                      "Percentage": GLib.Variant("d", 80.0)},
}
LOGIN_XML = """<node><interface name='org.freedesktop.login1.Manager'>
<method name='Inhibit'><arg type='s' direction='in'/><arg type='s' direction='in'/><arg type='s' direction='in'/>
<arg type='s' direction='in'/><arg type='h' direction='out'/></method></interface></node>"""
UP_XML = """<node><interface name='org.freedesktop.UPower'>
<property name='LidIsPresent' type='b' access='read'/><property name='LidIsClosed' type='b' access='read'/>
<property name='OnBattery' type='b' access='read'/></interface></node>"""
DEV_XML = """<node><interface name='org.freedesktop.UPower.Device'>
<property name='IsPresent' type='b' access='read'/><property name='Percentage' type='d' access='read'/>
</interface></node>"""
nxt = [0]
conn = [None]


def write_state():
    live = []
    for k, (fd, what) in list(inhib.items()):
        live.append(what)
    with open(STATE, "w") as f:
        f.write(f"{len(live)} {' '.join(live)}\n")


def on_method(c, sender, path, iface, method, params, inv):
    what = params.unpack()[0]
    r, w = os.pipe()
    nxt[0] += 1
    i = nxt[0]
    inhib[i] = (r, what)
    write_state()

    def watch(fd, cond):
        os.close(fd)
        inhib.pop(i, None)
        write_state()
        return False
    GLib.io_add_watch(r, GLib.IOCondition.HUP | GLib.IOCondition.IN, watch)
    fl = Gio.UnixFDList.new()
    idx = fl.append(w)
    os.close(w)
    inv.return_value_with_unix_fd_list(GLib.Variant("(h)", (idx,)), fl)


def getter(path):
    return lambda c, s, p, i, name: props[path].get(name)


def bus_acquired(c, name):
    conn[0] = c
    c.register_object("/org/freedesktop/login1", Gio.DBusNodeInfo.new_for_xml(LOGIN_XML).interfaces[0], on_method, None, None)
    for path, xml, iface in (("/org/freedesktop/UPower", UP_XML, 0), ("/org/freedesktop/UPower/devices/DisplayDevice", DEV_XML, 0)):
        c.register_object(path, Gio.DBusNodeInfo.new_for_xml(xml).interfaces[0], None, getter(path), None)
    write_state()
    print("ready", flush=True)


def change(path, iface, **kv):
    for k, v in kv.items():
        props[path][k] = v
    conn[0].emit_signal(None, path, "org.freedesktop.DBus.Properties", "PropertiesChanged",
                        GLib.Variant("(sa{sv}as)", (iface, kv, [])))


def stdin_loop():
    for line in sys.stdin:
        a = line.split()
        if a[0] == "lid":
            GLib.idle_add(lambda a=a: change("/org/freedesktop/UPower", "org.freedesktop.UPower",
                                             LidIsClosed=GLib.Variant("b", a[1] == "1")) and False)
        elif a[0] == "batt":
            def f(a=a):
                change("/org/freedesktop/UPower/devices/DisplayDevice", "org.freedesktop.UPower.Device",
                       Percentage=GLib.Variant("d", float(a[1])))
                change("/org/freedesktop/UPower", "org.freedesktop.UPower", OnBattery=GLib.Variant("b", a[2] == "1"))
                return False
            GLib.idle_add(f)


Gio.bus_own_name(Gio.BusType.SYSTEM, "org.freedesktop.login1", Gio.BusNameOwnerFlags.NONE, bus_acquired, None, None)
Gio.bus_own_name(Gio.BusType.SYSTEM, "org.freedesktop.UPower", Gio.BusNameOwnerFlags.NONE, None, None, None)
threading.Thread(target=stdin_loop, daemon=True).start()
GLib.MainLoop().run()
