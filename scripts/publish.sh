#!/bin/sh
# One-time: create the GitHub repo, set topics, push, cut v0.1.0. Needs gh logged in.
set -eu
cd "$(dirname "$0")/.."
gh repo create vishnuskandha/lidawake --public --source . --push \
  --description "Keep your Linux laptop awake with the lid closed. One click in the GNOME top bar."
for t in gnome-shell-extension ubuntu linux laptop power-management systemd gnome keep-awake lid; do
  gh repo edit --add-topic "$t"
done
# Tag push triggers CI, which builds the signed apt repo and the release (see docs/APT_SETUP.md).
git tag -a "v$(cat VERSION)" -m "v$(cat VERSION)" && git push --tags
echo "Now follow docs/APT_SETUP.md steps 1-2 (signing key secret) and 4 (enable Pages)."
