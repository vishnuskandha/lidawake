#!/bin/sh
DEST="${LIDAWAKE_HOME:-$HOME/.local/share/lidawake}"
pkill -f "python3 -m lidawake" 2>/dev/null
rm -f "$HOME/.local/bin/lidawake" "$HOME/.config/autostart/lidawake.desktop" "$HOME/.local/share/applications/lidawake.desktop"
rm -rf "$DEST" "$HOME/.config/lidawake"
gnome-extensions disable lidawake@vishnuskandha.github.io 2>/dev/null
rm -rf "$HOME/.local/share/gnome-shell/extensions/lidawake@vishnuskandha.github.io"
