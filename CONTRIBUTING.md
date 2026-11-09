# Contributing

Issues and PRs welcome.

```bash
python3 -m unittest discover -s tests
PYTHON=python3 ./tests/run_integration.sh   # needs xvfb, dbus, python3-gi
```

- Logic lives in `lidawake/policy.py` (pure, unit tested) and `lidawake/system.py` (D-Bus).
- The GNOME extension is `gnome-extension/lidawake@vishnuskandha.github.io/extension.js`. It controls the app through the `io.github.vishnuskandha.Lidawake` session-bus actions.
- Build packages: `scripts/build-deb.sh`, `scripts/build-extension-zip.sh`.
- Good first issues: Flatpak/AUR packaging, KDE/XFCE support, other distros, translations.
