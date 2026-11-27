#!/bin/sh
# ID-07: 現在の package.json と package-lock.json で固定した semver 7.7.4 を
# 一時ディレクトリへ導入し、その実体で API を一度だけ実行する。
# 実行: sh tools/id07_semver.sh
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
id07_dir="$here/id07"

npm_cache="${npm_config_cache:-${TMPDIR:-/tmp}/nako-id07-semver-cache}"
mkdir -p "$npm_cache"
export npm_config_cache="$npm_cache"
export npm_config_update_notifier=false

for command_name in node npm; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "FAIL ID-07 dependency: $command_name not found" >&2
    exit 2
  fi
done

for file in package.json package-lock.json check.mjs; do
  if [ ! -f "$id07_dir/$file" ]; then
    echo "FAIL ID-07 dependency: $id07_dir/$file is missing" >&2
    exit 2
  fi
done

work=$(mktemp -d "${TMPDIR:-/tmp}/nako-id07.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
cp "$id07_dir/package.json" "$id07_dir/package-lock.json" "$id07_dir/check.mjs" "$work/"

if ! (cd "$work" && npm ci --ignore-scripts --no-audit --no-fund --loglevel=error); then
  echo "FAIL ID-07 dependency: npm ci failed for the current package.json/package-lock.json" >&2
  exit 2
fi

out="$work/check.out"
set +e
node "$work/check.mjs" >"$out" 2>&1
rc=$?
set -e
cat "$out"

if [ "$rc" -eq 0 ]; then
  if ! grep -q '^ID-07 semver=7.7.4 ' "$out" \
    || ! grep -q '^PASS ID-07 1.9.0 ' "$out" \
    || ! grep -q '^PASS ID-07 2.0.0-alpha.2 ' "$out"; then
    echo "FAIL ID-07 dependency: expected API/PASS output is missing" >&2
    exit 2
  fi
  exit 0
fi

if ! grep -q '^ID-07 semver=7.7.4 ' "$out"; then
  echo "FAIL ID-07 dependency: API did not complete" >&2
  exit 2
fi
exit "$rc"
