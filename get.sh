#!/bin/sh
# One-line installer: curl -fsSL https://raw.githubusercontent.com/vishnuskandha/lidawake/main/get.sh | sh
set -eu
command -v apt-get >/dev/null 2>&1 || { echo "lidawake needs Debian/Ubuntu (apt)." >&2; exit 1; }
SUDO=""; [ "$(id -u)" = 0 ] || SUDO="sudo"
KEY=/usr/share/keyrings/lidawake.gpg
URL=https://vishnuskandha.github.io/lidawake
$SUDO apt-get install -y curl ca-certificates >/dev/null
curl -fsSL "$URL/lidawake.gpg" | $SUDO tee "$KEY" >/dev/null
echo "deb [signed-by=$KEY] $URL stable main" | $SUDO tee /etc/apt/sources.list.d/lidawake.list >/dev/null
$SUDO apt-get update
$SUDO apt-get install -y lidawake
echo
echo "Done. Log out and back in once so GNOME loads the top-bar extension."
echo "Updates arrive via: sudo apt update && sudo apt upgrade"
