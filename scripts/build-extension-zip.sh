#!/bin/sh
# Builds the zip for extensions.gnome.org upload -> dist/lidawake-extension.zip
set -eu
cd "$(dirname "$0")/../gnome-extension/lidawake@vishnuskandha.github.io"
mkdir -p ../../dist && rm -f ../../dist/lidawake-extension.zip
zip -qr ../../dist/lidawake-extension.zip metadata.json extension.js icons
echo dist/lidawake-extension.zip
