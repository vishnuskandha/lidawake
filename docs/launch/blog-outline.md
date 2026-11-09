# Post: "Why closing the lid kills your build (and how logind inhibitors fix it)"
1. The problem: lid close -> logind -> suspend. Why Caffeine doesn't help.
2. What a logind inhibitor is. `systemd-inhibit --what=handle-lid-switch`. Block vs delay.
3. Doing it from an app: the Inhibit() D-Bus call returns an fd; close it to release. Crash-safe by construction.
4. UPower for lid and battery state.
5. Driving a GNOME Shell extension from a Python app with a Gio action group.
6. Gotchas: external display docking, extension shell-version metadata, Wayland needs logout to load extensions.
Tags: linux, gnome, systemd, python. Cross-post to dev.to, Hashnode, r/linux.
