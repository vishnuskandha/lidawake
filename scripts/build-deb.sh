#!/bin/sh
# Usage: scripts/build-deb.sh [version]  -> dist/lidawake_<version>_all.deb
set -eu
cd "$(dirname "$0")/.."
VER="${1:-$(cat VERSION)}"
EXT=awayke@daemonphantom.github.io
ROOT=$(mktemp -d)
install -d "$ROOT/DEBIAN" "$ROOT/usr/lib/lidawake" "$ROOT/usr/share/lidawake/icons" "$ROOT/usr/bin" \
  "$ROOT/usr/share/applications" "$ROOT/etc/xdg/autostart" "$ROOT/usr/share/gnome-shell/extensions/$EXT" \
  "$ROOT/usr/share/doc/lidawake"
cp -r awayke "$ROOT/usr/lib/lidawake/awayke"
find "$ROOT" -name __pycache__ -prune -exec rm -rf {} +
cp icons/*.svg "$ROOT/usr/share/lidawake/icons/"
cp -r gnome-extension/$EXT/. "$ROOT/usr/share/gnome-shell/extensions/$EXT/"
cp LICENSE "$ROOT/usr/share/doc/lidawake/copyright"
cat > "$ROOT/usr/bin/awayke" <<'LAUNCH'
#!/bin/sh
export PYTHONPATH="/usr/lib/lidawake${PYTHONPATH:+:$PYTHONPATH}"
export AWAYKE_HOME="${AWAYKE_HOME:-/usr/share/lidawake}"
exec /usr/bin/python3 -m awayke "$@"
LAUNCH
chmod 755 "$ROOT/usr/bin/awayke"
ENTRY="[Desktop Entry]
Type=Application
Name=Awayke
Comment=Keep your laptop awake with the lid closed
Exec=/usr/bin/awayke
Icon=/usr/share/lidawake/icons/awayke-on.svg
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true"
printf '%s\n' "$ENTRY" > "$ROOT/usr/share/applications/awayke.desktop"
printf '%s\n' "$ENTRY" > "$ROOT/etc/xdg/autostart/awayke.desktop"
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
 sessions and low-battery auto-off. Linux port of Awayke.
CTL
mkdir -p dist
dpkg-deb --root-owner-group --build "$ROOT" "dist/lidawake_${VER}_all.deb" >/dev/null
rm -rf "$ROOT"
echo "dist/lidawake_${VER}_all.deb"
