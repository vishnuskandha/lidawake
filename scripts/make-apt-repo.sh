#!/bin/sh
# Build a signed apt repo in <site_dir> from <site_dir>/pool/*.deb.
# Usage: make-apt-repo.sh <site_dir> <gpg_key_id> [passphrase_file]
set -eu
SITE=$1; KEY=$2; PASSFILE=${3:-}
cd "$SITE"
mkdir -p dists/stable/main/binary-all
apt-ftparchive packages pool > dists/stable/main/binary-all/Packages
gzip -9kf dists/stable/main/binary-all/Packages
CONF=$(mktemp)
cat > "$CONF" <<'CFG'
APT::FTPArchive::Release::Origin "lidawake";
APT::FTPArchive::Release::Label "lidawake";
APT::FTPArchive::Release::Suite "stable";
APT::FTPArchive::Release::Codename "stable";
APT::FTPArchive::Release::Architectures "all";
APT::FTPArchive::Release::Components "main";
CFG
apt-ftparchive -c "$CONF" release dists/stable > dists/stable/Release.tmp
mv dists/stable/Release.tmp dists/stable/Release
rm -f "$CONF" dists/stable/Release.gpg dists/stable/InRelease
if [ -n "$PASSFILE" ]; then P="--pinentry-mode loopback --passphrase-file $PASSFILE"; else P="--pinentry-mode loopback --passphrase ''"; fi
# shellcheck disable=SC2086
gpg --batch --yes --default-key "$KEY" $P -abs -o dists/stable/Release.gpg dists/stable/Release
# shellcheck disable=SC2086
gpg --batch --yes --default-key "$KEY" $P --clearsign -o dists/stable/InRelease dists/stable/Release
gpg --batch --yes --export "$KEY" > lidawake.gpg
echo "repo ready in $SITE"
