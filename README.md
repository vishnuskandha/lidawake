<h1 align="center">lidawake</h1>
<p align="center">
<a href="https://github.com/vishnuskandha/lidawake/actions/workflows/test.yml"><img src="https://github.com/vishnuskandha/lidawake/actions/workflows/test.yml/badge.svg" alt="tests"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-666666" alt="MIT"></a>
<img src="https://img.shields.io/badge/GNOME-46--51-4a86cf" alt="GNOME 46-51">
</p>

<p align="center"><img src="docs/demo.gif" alt="lidawake demo" width="360"></p>

<p align="center"><b>Keep your Linux laptop awake with the lid closed.</b><br>One click in the GNOME top bar. No root, no daemon, no config files.</p>
<p align="center"><img src="docs/icons.png" width="320" alt="Closed eyelid = off, open eye = on"></p>

Close the lid and Ubuntu suspends. lidawake puts an eye in the top bar: **closed eyelid = inactive, open eye = awake**. Click it, close the lid, and the laptop keeps running builds, downloads, servers and long AI-agent sessions.

> Linux port of [Awayke](https://github.com/daemonphantom/Awayke) (macOS, MIT) by daemonphantom. Same idea and behaviour, new implementation for logind/GNOME.

## Features

- Top bar button next to the control centre (GNOME 46-51), plus an optional tray icon
- Timed sessions: 15 min, 30 min, 1 h, 2 h, indefinitely, or **until the lid is reopened**
- Auto-off at 10/20/30% battery, resumes once you plug in
- Crash-safe: sleep can never get stuck disabled (the kernel drops the lock if the app dies)
- No sudo at runtime

## Install (Ubuntu 24.04+)

**One line (adds the signed APT repo, auto-updates with `sudo apt update && sudo apt upgrade`):**

```bash
curl -fsSL https://raw.githubusercontent.com/vishnuskandha/lidawake/main/get.sh | sh
```

**APT, manual steps:**

```bash
curl -fsSL https://vishnuskandha.github.io/lidawake/lidawake.gpg | sudo tee /usr/share/keyrings/lidawake.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/lidawake.gpg] https://vishnuskandha.github.io/lidawake stable main" | sudo tee /etc/apt/sources.list.d/lidawake.list
sudo apt update && sudo apt install lidawake
```

**.deb only (no auto-update):** download `lidawake_*_all.deb` from [Releases](https://github.com/vishnuskandha/lidawake/releases/latest), then:

```bash
sudo apt install ./lidawake_*_all.deb
```

**From source:**

```bash
git clone https://github.com/vishnuskandha/lidawake.git
cd lidawake && ./install.sh
```

Then log out and back in once so GNOME loads the extension. The app command is `lidawake`.

## How it works

lidawake holds a logind **block inhibitor** (`handle-lid-switch:sleep:idle`) over D-Bus, the same mechanism as `systemd-inhibit`. Releasing it restores normal lid behaviour. Lid state and battery come from UPower. The GNOME extension talks to the app over a session-bus action group.

| | lidawake | `systemd-inhibit` | Caffeine-type extensions |
|---|:-:|:-:|:-:|
| Blocks lid-close suspend | yes | yes (manual command) | usually no |
| One-click toggle | yes | no | yes |
| Timed / until-lid-reopen | yes | no | partly |
| Low-battery cutoff | yes | no | no |

## Status

Beta. The logic is covered by unit tests and an integration test against mocked logind/UPower. Real-lid testing so far is on Ubuntu with GNOME 50 only. Please open an issue with your distro, GNOME version and `systemd-inhibit --list` output if something misbehaves.

## Caveats

- Don't put a lid-closed, running laptop in a bag. It gets hot. Keep it on AC for long sessions.
- Docked with an external display, logind already ignores the lid.
- GNOME needs the AppIndicator extension for the tray icon (Ubuntu enables it by default).

## Uninstall

`~/.local/share/lidawake/uninstall.sh`, or "Uninstall" in the tray menu.

## Development

```bash
python3 -m unittest discover -s tests
PYTHON=python3 ./tests/run_integration.sh   # needs xvfb, dbus
```

## License

MIT. See [LICENSE](LICENSE). Based on Awayke by daemonphantom.
