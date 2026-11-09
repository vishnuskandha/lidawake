#!/bin/sh
# One-time: create the GitHub repo, set topics, push, cut v0.1.0. Needs gh logged in.
set -eu
cd "$(dirname "$0")/.."
gh repo create vishnuskandha/lidawake --public --source . --push \
  --description "Keep your Linux laptop awake with the lid closed. One click in the GNOME top bar."
for t in gnome-shell-extension ubuntu linux laptop power-management systemd gnome keep-awake lid; do
  gh repo edit --add-topic "$t"
done
scripts/build-deb.sh >/dev/null; scripts/build-extension-zip.sh >/dev/null
git tag -a "v$(cat VERSION)" -m "v$(cat VERSION)" && git push --tags
gh release create "v$(cat VERSION)" dist/*.deb dist/lidawake-extension.zip \
  --title "lidawake v$(cat VERSION)" --notes-file CHANGELOG.md
