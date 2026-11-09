# Show HN (weekday, ~9-11am US Eastern; answer every comment)

**Title:** Show HN: lidawake – keep a Linux laptop awake with the lid closed

**First comment (post it yourself):**
Closing the lid suspends Linux laptops, which kills long-running jobs. systemd-inhibit can block that, but it's a manual command that you have to keep alive in a terminal. lidawake wraps it in a top bar toggle, with timers, an "until lid reopens" mode and a low-battery cutoff.

Implementation: Python/GTK app takes a logind block inhibitor (handle-lid-switch:sleep:idle) over D-Bus and reads lid/battery from UPower. The GNOME Shell extension drives the app through a session-bus action group. Tests run against a mocked logind/UPower on a private bus in CI.

Limits: it's a beta, tested on GNOME 50 only so far. Docked with an external display, logind already ignores the lid. Don't put a running closed laptop in a bag.

Based on Awayke (macOS, MIT) by daemonphantom. Feedback on other desktops/distros welcome.
