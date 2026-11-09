#!/bin/sh
# Lidawake installer for Ubuntu/Debian (GNOME). Usage: ./install.sh [--no-autostart] [--no-apt]
set -eu
SRC=$(cd "$(dirname "$0")" && pwd)
DEST="${LIDAWAKE_HOME:-$HOME/.local/share/lidawake}"
BIN="$HOME/.local/bin"
AUTOSTART=1; APT=1
for a in "$@"; do
  case $a in --no-autostart) AUTOSTART=0 ;; --no-apt) APT=0 ;; esac
done

if [ "$APT" = 1 ] && command -v apt-get >/dev/null 2>&1; then
  need=""
  for p in python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 librsvg2-common; do
    dpkg -s "$p" >/dev/null 2>&1 || need="$need $p"
  done
  if [ -n "$need" ]; then
    echo "Installing:$need"
    sudo apt-get install -y $need
  fi
fi

rm -rf "$DEST/lidawake"
mkdir -p "$DEST/icons" "$BIN" "$HOME/.local/share/applications"
cp -r "$SRC/lidawake" "$DEST/lidawake"
find "$DEST/lidawake" -name __pycache__ -prune -exec rm -rf {} +
cp "$SRC"/icons/*.svg "$DEST/icons/"
cp "$SRC/uninstall.sh" "$DEST/uninstall.sh"

cat > "$BIN/lidawake" <<LAUNCH
#!/bin/sh
export PYTHONPATH="$DEST\${PYTHONPATH:+:\$PYTHONPATH}"
export LIDAWAKE_HOME="$DEST"
exec /usr/bin/python3 -m lidawake "\$@"
LAUNCH
chmod +x "$BIN/lidawake"

ENTRY="[Desktop Entry]
Type=Application
Name=Lidawake
Comment=Keep your laptop awake with the lid closed
Exec=$BIN/lidawake
Icon=$DEST/icons/lidawake-on.svg
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true"
printf '%s\n' "$ENTRY" > "$HOME/.local/share/applications/lidawake.desktop"
if [ "$AUTOSTART" = 1 ]; then
  mkdir -p "$HOME/.config/autostart"
  printf '%s\n' "$ENTRY" > "$HOME/.config/autostart/lidawake.desktop"
fi

EXT=lidawake@vishnuskandha.github.io
if command -v gnome-extensions >/dev/null 2>&1; then
  EXTDIR="$HOME/.local/share/gnome-shell/extensions/$EXT"
  rm -rf "$EXTDIR"; mkdir -p "$EXTDIR"
  cp -r "$SRC/gnome-extension/$EXT/." "$EXTDIR/"
  gnome-extensions enable "$EXT" 2>/dev/null || EXT_PENDING=1
  echo "Top bar button installed. Log out and back in once to activate it."
fi

echo "Installed. Run: $BIN/lidawake  (or find Lidawake in the app grid)"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "Note: add $BIN to PATH." ;; esac
