#!/bin/sh
# Needs: dbus-daemon, xvfb-run, python3-gi, gir1.2-ayatanaappindicator3-0.1
cd "$(dirname "$0")/.." || exit 1
export MOCK_STATE=$(mktemp) AWAYKE_HOME=$(mktemp -d) XDG_CONFIG_HOME=$(mktemp -d)
mkdir -p "$AWAYKE_HOME/icons"; cp icons/*.svg "$AWAYKE_HOME/icons/"
exec dbus-run-session -- sh -c '
  export DBUS_SYSTEM_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS
  exec xvfb-run -a ${PYTHON:-/usr/bin/python3} tests/integration.py'
