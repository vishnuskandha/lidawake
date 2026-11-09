## v0.2.2

- The app enables its GNOME extension on first run, so a fresh `.deb` install shows the header icon after one login (a manual disable is respected)

## v0.2.1

- Signed APT repository: `sudo apt update && sudo apt upgrade` now delivers new versions
- The package ships its own apt source and key

## v0.2.0

- Renamed the app, command, extension and data dirs to **lidawake** (existing settings are migrated)
- Header menu shows the current session mode (dot) and updates live when you switch modes
- Timers now keep counting while the machine is suspended (boot clock instead of monotonic)
- "Until lid is reopened" is disabled when the lid state is unavailable
- Safer settings write, extension no longer double-launches the app

## v0.1.0

First release. Linux port of Awayke.

- GNOME top bar button (closed eyelid = off, open eye = on), GNOME 46-51
- Tray icon (AppIndicator)
- Timed sessions, until-lid-reopens, indefinite
- Low-battery auto-off (10/20/30%)
- logind block inhibitor, no root, crash-safe
- `.deb` package and install script
