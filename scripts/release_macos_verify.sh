#!/bin/sh
# Verify the packaged macOS .app is signed and the .dmg is stapled.
set -eu

bundle="${GITHUB_WORKSPACE}/apps/desktop/src-tauri/target/release/bundle"
app="$(find "${bundle}/macos" -maxdepth 1 -name '*.app' -type d | head -n 1)"
dmg="$(find "${bundle}/dmg" -maxdepth 1 -name '*.dmg' -type f | head -n 1)"

if [ -z "${app}" ]; then
  echo "No macOS .app found under ${bundle}/macos" >&2
  exit 1
fi
if [ -z "${dmg}" ]; then
  echo "No macOS .dmg found under ${bundle}/dmg" >&2
  exit 1
fi

codesign --verify --deep --strict --verbose=2 "${app}"
xcrun stapler validate "${dmg}"
echo "macOS .app code signature verified and .dmg staple validated."
