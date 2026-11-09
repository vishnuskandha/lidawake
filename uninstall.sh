#!/bin/sh
DEST="${AWAYKE_HOME:-$HOME/.local/share/awayke}"
pkill -f "python3 -m awayke" 2>/dev/null
rm -f "$HOME/.local/bin/awayke" "$HOME/.config/autostart/awayke.desktop" "$HOME/.local/share/applications/awayke.desktop"
rm -rf "$DEST" "$HOME/.config/awayke"
gnome-extensions disable awayke@daemonphantom.github.io 2>/dev/null
rm -rf "$HOME/.local/share/gnome-shell/extensions/awayke@daemonphantom.github.io"
