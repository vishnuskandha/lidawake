#!/bin/sh
# Builds the zip for extensions.gnome.org upload -> dist/awayke-extension.zip
set -eu
cd "$(dirname "$0")/../gnome-extension/awayke@daemonphantom.github.io"
mkdir -p ../../dist && rm -f ../../dist/awayke-extension.zip
zip -qr ../../dist/awayke-extension.zip metadata.json extension.js icons
echo dist/awayke-extension.zip
