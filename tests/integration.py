"""End-to-end test against mock logind/UPower. Run via tests/run_integration.sh."""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gi.repository import GLib  # noqa: E402

state = os.environ["MOCK_STATE"]
mock = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "mock_system.py")],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
assert mock.stdout.readline().strip() == "ready"

from lidawake.app import Lidawake, now  # noqa: E402

app = Lidawake()
app.register(None)
app.do_startup() if False else None  # startup fires on register()
ctx = GLib.MainContext.default()


def pump(sec=0.4):
    end = time.time() + sec
    while time.time() < end:
        while ctx.pending():
            ctx.iteration(False)
        time.sleep(0.01)


def inhibitors():
    pump(0.3)
    return int(open(state).read().split()[0])


def mock_cmd(c):
    mock.stdin.write(c + "\n"); mock.stdin.flush(); pump(0.5)


fails = 0


def check(cond, name):
    global fails
    print(("ok - " if cond else "FAIL - ") + name)
    fails += not cond


check(app.lid.is_closed is False, "lid state read from UPower")
check(app.last_snapshot == (80, True), "battery snapshot read from UPower")
check(inhibitors() == 0, "no inhibitor at start")

app.set_intent(True); pump()
check(inhibitors() == 1 and app.effective_active, "turn on acquires one logind inhibitor")
check("handle-lid-switch" in open(state).read(), "inhibitor blocks handle-lid-switch")
app.set_intent(True); pump()
check(inhibitors() == 1, "re-enable does not leak a second inhibitor")
app.set_intent(False); pump()
check(inhibitors() == 0 and not app.effective_active, "turn off releases inhibitor")

# session-bus action group (what the GNOME extension uses)
from gi.repository import Gio  # noqa: E402
grp = Gio.DBusActionGroup.get(Gio.bus_get_sync(Gio.BusType.SESSION, None), "io.github.vishnuskandha.Lidawake",
                              "/io/github/vishnuskandha/Lidawake")
grp.list_actions(); pump(0.5)
check(grp.get_action_state("active").get_boolean() is False, "action group exposes active=false")
grp.activate_action("active", None); pump(0.6)
check(app.effective_active and inhibitors() == 1, "action 'active' turns on")
check(grp.get_action_state("active").get_boolean() is True, "action state follows app")
grp.activate_action("keep-for", GLib.Variant("i", 30)); pump(0.6)
check(app.remaining is not None and 1790 < app.remaining <= 1800, "action 'keep-for' arms 30m timer")
check("30m" in grp.get_action_state("status").get_string() or "left" in grp.get_action_state("status").get_string(), "status string updates")
grp.activate_action("active", None); pump(0.6)
check(not app.intent and inhibitors() == 0, "action 'active' turns off")
grp.activate_action("auto-off", GLib.Variant("i", 20)); pump(0.6)
check(app.threshold == 20 and grp.get_action_state("auto-off").get_int32() == 20, "action 'auto-off' sets threshold")
grp.activate_action("auto-off", GLib.Variant("i", 7)); pump(0.4)
check(app.threshold == 20, "action 'auto-off' rejects invalid value")

# live mode changes while active
def mode():
    pump(0.5)
    return grp.get_action_state("mode").get_string()

grp.activate_action("active", None); pump(0.5)
check(mode() == "indefinite", "mode: indefinite after turning on")
grp.activate_action("keep-for", GLib.Variant("i", -1))
check(mode() == "lid" and app.deadline is None, "live: indefinite -> until lid reopens")
grp.activate_action("keep-for", GLib.Variant("i", 15))
check(mode() == "timer:15" and not app.lid_session.is_active, "live: lid -> 15m timer")
grp.activate_action("keep-for", GLib.Variant("i", 60))
check(mode() == "timer:60" and 3500 < app.remaining <= 3600, "live: 15m -> 1h timer re-arms")
grp.activate_action("keep-for", GLib.Variant("i", -1))
check(mode() == "lid" and app.deadline is None, "live: timer -> until lid reopens")
grp.activate_action("keep-for", GLib.Variant("i", 0))
check(mode() == "indefinite" and not app.lid_session.is_active, "live: lid -> indefinite")
check(inhibitors() == 1, "lock held through all live changes")
grp.activate_action("keep-for", GLib.Variant("i", -1)); pump(0.4)
mock_cmd("lid 1"); mock_cmd("lid 0")
check(mode() == "off" and inhibitors() == 0, "live-armed lid session ends on reopen")

# until lid reopens
app.set_intent(True, until_lid=True)
check(app.lid_session.is_waiting_for_close, "lid session waits for close")
mock_cmd("lid 1"); check(app.intent, "still on while lid closed")
mock_cmd("lid 0"); check(not app.intent and inhibitors() == 0, "lid reopen ends session and releases")

# timer
app.set_intent(True, timer_minutes=1)
check(app.remaining is not None and 55 < app.remaining <= 60, "timer armed")
app.deadline = now() - 1; app._tick(); pump()
check(not app.intent and inhibitors() == 0, "timer expiry turns off")

# battery auto-off
app.threshold = 20
mock_cmd("batt 50 1")
app.set_intent(True); pump()
mock_cmd("batt 15 1")
check(app.suspended and inhibitors() == 0, "battery below floor releases inhibitor")
mock_cmd("batt 30 0")
check(not app.suspended and inhibitors() == 1, "AC + hysteresis resumes")
app.set_intent(False)

# release on process death is kernel-level: simulate by dropping fd without release()
app.set_intent(True); pump()
os.close(app.inhibitor._fd); app.inhibitor._fd = None
check(inhibitors() == 0, "closing fd (crash path) releases inhibitor")

app.quit_app() if False else app.inhibitor.release()
mock.terminate()
print("all passing" if not fails else f"{fails} failing")
sys.exit(1 if fails else 0)
