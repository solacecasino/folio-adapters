#!/bin/sh
# Builds the Rust adapters and packs one zip per adapter into dist/.
# Each zip holds a single folder with adapter.toml, ready for
# Folio → Adapters… → Add Adapter…
# Usage: scripts/build.sh
set -e
cd "$(dirname "$0")/.."
rm -rf dist && mkdir -p dist/stage

for dir in */; do
  name=${dir%/}
  [ -f "$name/adapter.toml" ] || continue
  version=$(sed -n 's/^version = "\(.*\)"/\1/p' "$name/adapter.toml" | head -1)
  suffix=""
  if [ -f "$name/build.sh" ]; then
    sh "$name/build.sh"
    suffix="-macos-arm64"   # compiled adapters are Apple Silicon builds
  fi
  # Ship only what Folio needs to run it: no sources or build output.
  rsync -a --exclude target --exclude src --exclude tests --exclude 'Cargo.*' \
    --exclude build.sh --exclude .gitignore --exclude __pycache__ "$name/" "dist/stage/$name/"
  (cd dist/stage && ditto -c -k --norsrc --noextattr --keepParent "$name" "../$name-$version$suffix.zip")
  echo "Built dist/$name-$version$suffix.zip"
done
rm -rf dist/stage
