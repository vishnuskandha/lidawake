#!/bin/sh
# Usage: scripts/build-deb.sh [version]  -> dist/lidawake_<version>_all.deb
set -eu
cd "$(dirname "$0")/.."
VER="${1:-$(cat VERSION)}"
EXT=lidawake@vishnuskandha.github.io
ROOT=$(mktemp -d)
install -d "$ROOT/DEBIAN" "$ROOT/usr/lib/lidawake" "$ROOT/usr/share/lidawake/icons" "$ROOT/usr/bin" \
  "$ROOT/usr/share/applications" "$ROOT/etc/xdg/autostart" "$ROOT/usr/share/gnome-shell/extensions/$EXT" \
  "$ROOT/usr/share/doc/lidawake"
cp -r lidawake "$ROOT/usr/lib/lidawake/lidawake"
find "$ROOT" -name __pycache__ -prune -exec rm -rf {} +
cp icons/*.svg "$ROOT/usr/share/lidawake/icons/"
cp -r gnome-extension/$EXT/. "$ROOT/usr/share/gnome-shell/extensions/$EXT/"
cp LICENSE "$ROOT/usr/share/doc/lidawake/copyright"
cat > "$ROOT/usr/bin/lidawake" <<'LAUNCH'
#!/bin/sh
export PYTHONPATH="/usr/lib/lidawake${PYTHONPATH:+:$PYTHONPATH}"
export LIDAWAKE_HOME="${LIDAWAKE_HOME:-/usr/share/lidawake}"
exec /usr/bin/python3 -m lidawake "$@"
LAUNCH
chmod 755 "$ROOT/usr/bin/lidawake"
ENTRY="[Desktop Entry]
Type=Application
Name=Lidawake
Comment=Keep your laptop awake with the lid closed
Exec=/usr/bin/lidawake
Icon=/usr/share/lidawake/icons/lidawake-on.svg
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true"
printf '%s\n' "$ENTRY" > "$ROOT/usr/share/applications/lidawake.desktop"
printf '%s\n' "$ENTRY" > "$ROOT/etc/xdg/autostart/lidawake.desktop"
cat > "$ROOT/DEBIAN/control" <<CTL
Package: lidawake
Version: $VER
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-gi, gir1.2-gtk-3.0, gir1.2-ayatanaappindicator3-0.1, librsvg2-common, systemd, upower
Recommends: gnome-shell-extension-appindicator
Maintainer: Vishnu Skandha <vishnu.skandha@gmail.com>
Homepage: https://github.com/vishnuskandha/lidawake
Description: Keep a laptop awake with the lid closed
 One-click GNOME top bar button and tray app that holds a logind inhibitor so
 closing the lid does not suspend the machine. Timed sessions, until-lid-reopens
 sessions and low-battery auto-off. Linux port of Lidawake.
CTL
cat > "$ROOT/DEBIAN/postinst" <<'POST'
#!/bin/sh
# Migrate from the pre-rename build (command "awayke"): stop it so it releases its lock.
pkill -f "python3 -m awayke" 2>/dev/null || true
exit 0
POST
cat > "$ROOT/DEBIAN/prerm" <<'PRE'
#!/bin/sh
pkill -f "python3 -m lidawake" 2>/dev/null || true
exit 0
PRE
chmod 755 "$ROOT/DEBIAN/postinst" "$ROOT/DEBIAN/prerm"
mkdir -p dist
dpkg-deb --root-owner-group --build "$ROOT" "dist/lidawake_${VER}_all.deb" >/dev/null
rm -rf "$ROOT"
echo "dist/lidawake_${VER}_all.deb"
