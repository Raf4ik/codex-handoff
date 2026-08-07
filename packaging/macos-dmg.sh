#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
stage="$project_root/dist/dmg-stage"
application="$project_root/dist/CodexHandoff.app"
icon="$project_root/build/icons/CodexHandoff.icns"
destination="$project_root/dist/CodexHandoff-macOS-arm64.dmg"

if [[ ! -d "$application" ]]; then
  echo "Application bundle not found: $application" >&2
  exit 1
fi

rm -rf "$stage"
mkdir -p "$stage"
cp -R "$application" "$stage/CodexHandoff.app"
ln -s /Applications "$stage/Applications"
cp "$icon" "$stage/.VolumeIcon.icns"
if command -v SetFile >/dev/null 2>&1; then
  SetFile -a C "$stage"
fi
for attempt in 1 2 3; do
  if hdiutil create -volname "Codex Handoff" -srcfolder "$stage" \
    -ov -format UDZO "$destination"; then
    exit 0
  fi

  if [[ "$attempt" -eq 3 ]]; then
    echo "Failed to create disk image after $attempt attempts" >&2
    exit 1
  fi

  echo "Disk image creation failed (attempt $attempt); retrying..." >&2
  rm -f "$destination"
  sleep 3
done
