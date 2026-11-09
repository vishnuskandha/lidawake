# One-time setup for apt updates

1. Make a signing key (no expiry, keep the backup private):
   ```bash
   gpg --quick-generate-key "lidawake apt <vishnu.skandha@gmail.com>" rsa4096 sign never
   gpg --armor --export-secret-keys "lidawake apt" > lidawake-private.asc
   ```
2. GitHub repo -> Settings -> Secrets and variables -> Actions: add `GPG_PRIVATE_KEY` (contents of the .asc) and, if you set a passphrase, `GPG_PASSPHRASE`.
3. Push the repo, then tag a release: `git tag v0.2.1 && git push --tags`. CI builds the .deb, signs the apt repo and pushes it to the `gh-pages` branch.
4. Settings -> Pages -> Source: deploy from branch `gh-pages` / root.
5. Users add the repo once (commands on https://vishnuskandha.github.io/lidawake/). From v0.2.1 the package ships its own apt source, so later `sudo apt update && sudo apt upgrade` pulls new versions.

Releasing an update: bump `VERSION` and `CHANGELOG.md`, commit, `git tag vX.Y.Z && git push --tags`.
Never lose the private key: users trust that key; a new key means everyone re-adds the repo.
