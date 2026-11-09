# Submit to extensions.gnome.org
1. `scripts/build-extension-zip.sh` -> `dist/lidawake-extension.zip`
2. Sign in at https://extensions.gnome.org/upload/ and upload the zip.
3. Review notes to include: the extension has no network access, spawns only `~/.local/bin/lidawake` or `/usr/bin/lidawake`, and talks to the app over the session bus.
4. The uuid is `lidawake@vishnuskandha.github.io` and `url` points at your repo. Keep both stable after the first upload; changing the uuid creates a new extension.
5. Review takes days to weeks. Reviewers reject code that leaves signals connected after disable(); this one disconnects them in destroy().
