# Submit to extensions.gnome.org
1. `scripts/build-extension-zip.sh` -> `dist/awayke-extension.zip`
2. Sign in at https://extensions.gnome.org/upload/ and upload the zip.
3. Review notes to include: the extension has no network access, spawns only `~/.local/bin/awayke` or `/usr/bin/awayke`, and talks to the app over the session bus.
4. Before submitting: the uuid `awayke@daemonphantom.github.io` and `url` in metadata.json should point to your repo/domain. Change them if you want your own namespace (e.g. `lidawake@vishnuskandha.github.io`), in metadata.json, install.sh, uninstall.sh and scripts/build-deb.sh.
5. Review takes days to weeks. Reviewers reject code that leaves signals connected after disable(); this one disconnects them in destroy().
