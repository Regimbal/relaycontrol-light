#!/bin/sh
. /etc/profile
cd /usr/share/relaycontrol-light/
exec python3 src/main.py --config config/config.yaml