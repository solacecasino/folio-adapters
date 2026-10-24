#!/bin/sh
# Builds every adapter for this computer and makes one zip per adapter in
# dist/. See scripts/build.py.
exec python3 "$(dirname "$0")/build.py" "$@"
