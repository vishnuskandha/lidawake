# Reddit (r/gnome, r/Ubuntu, r/linux). One per day. Read each sub's self-promo rules first.

**Title:** I got tired of my laptop suspending mid-build, so I made a one-click "keep awake with the lid closed" button for the GNOME top bar

**Body:**
Closing the lid on Ubuntu suspends the machine, which kills long builds, downloads and agent sessions. Caffeine-style extensions stop idle sleep but not lid-close suspend.

lidawake holds a logind inhibitor for the lid switch, so it works without root or editing logind.conf. Closed eyelid in the top bar = off, open eye = on. Click it, close the lid, walk away.

- timed sessions (15m-2h) or "until I reopen the lid"
- auto-off at 10/20/30% battery
- crash-safe: if the app dies the kernel releases the lock
- .deb + GNOME extension (46-51)

It's a Linux port of Awayke (macOS). Beta: tested on Ubuntu/GNOME 50, feedback on other setups very welcome.

GitHub: https://github.com/vishnuskandha/lidawake

[attach GIF]
