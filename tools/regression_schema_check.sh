#!/bin/sh
# P01 の異常系を短く再現する。追跡ファイルは変更せず、一時コピーだけを使う。
# 実行: sh tools/regression_schema_check.sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/nako-p01-regression.XXXXXX")
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

export UV_CACHE_DIR="${UV_CACHE_DIR:-${TMPDIR:-/tmp}/nako-p01-uv-cache}"
export npm_config_cache="${npm_config_cache:-${TMPDIR:-/tmp}/nako-id07-semver-cache}"
export npm_config_update_notifier=false

pass() { echo "PASS $*"; }
fail() { echo "FAIL $*" >&2; exit 1; }
hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

schema_copy() {
  dir="$tmp/$1"
  mkdir -p "$dir/schemas/v1" "$dir/fixtures/v1/requirements" "$dir/tools"
  cp "$root"/schemas/v1/*.json "$dir/schemas/v1/"
  cp "$root"/fixtures/v1/requirements/* "$dir/fixtures/v1/requirements/"
  cp "$root"/tools/schema_check.py "$root"/tools/schema_check.py.lock "$dir/tools/"
  echo "$dir"
}

expect_check_failure() {
  label="$1"
  dir="$2"
  pattern="$3"
  if (cd "$dir" && uv run --script --locked tools/schema_check.py check >check.out 2>&1); then
    fail "$label: check unexpectedly succeeded"
  fi
  grep -q "$pattern" "$dir/check.out" || {
    cat "$dir/check.out" >&2
    fail "$label: missing diagnostic $pattern"
  }
  pass "$label"
}

mutate_ref() {
  file="$1"
  ref="$2"
  python3 - "$file" "$ref" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
schema = json.loads(path.read_text())
schema["properties"]["runtime-dependencies"]["properties"]["wnako"] = {"$ref": sys.argv[2]}
path.write_text(json.dumps(schema))
PY
}

case_dir=$(schema_copy broken-internal-ref)
mutate_ref "$case_dir/schemas/v1/nako-manifest.schema.json" '#/$defs/missingDefinition'
expect_check_failure "broken internal ref fails even on an unused branch" "$case_dir" 'cannot resolve local \$ref'

case_dir=$(schema_copy broken-file-ref)
mutate_ref "$case_dir/schemas/v1/nako-manifest.schema.json" 'missing.schema.json#/$defs/relativePath'
expect_check_failure "broken file ref fails" "$case_dir" 'cannot resolve local \$ref'

case_dir=$(schema_copy remote-ref)
mutate_ref "$case_dir/schemas/v1/nako-manifest.schema.json" 'https://example.invalid/schema.json'
expect_check_failure "remote ref fails" "$case_dir" 'remote \$ref is not allowed'

case_dir=$(schema_copy non-schema-string-ref)
mutate_ref "$case_dir/schemas/v1/nako-manifest.schema.json" 'npkg-metadata.schema.json#/required/0'
expect_check_failure "non-schema string target fails" "$case_dir" 'not a JSON Schema'

case_dir=$(schema_copy non-schema-number-ref)
mutate_ref "$case_dir/schemas/v1/nako-manifest.schema.json" 'npkg-metadata.schema.json#/properties/schema_version/const'
expect_check_failure "non-schema number target fails" "$case_dir" 'not a JSON Schema'

case_dir=$(schema_copy non-schema-array-ref)
mutate_ref "$case_dir/schemas/v1/nako-manifest.schema.json" 'npkg-metadata.schema.json#/required'
expect_check_failure "non-schema array target fails" "$case_dir" 'not a JSON Schema'

case_dir=$(schema_copy boolean-schema-ref)
python3 - "$case_dir/schemas/v1/nako-manifest.schema.json" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
schema = json.loads(path.read_text())
schema["$defs"]["booleanSchema"] = True
schema["properties"]["runtime-dependencies"]["properties"]["wnako"] = {
    "$ref": "#/$defs/booleanSchema"
}
path.write_text(json.dumps(schema))
PY
if ! (cd "$case_dir" && uv run --script --locked tools/schema_check.py check >check.out 2>&1); then
  cat "$case_dir/check.out" >&2
  fail "boolean schema target: check unexpectedly failed"
fi
pass "boolean schema target is accepted"

manifest_dir="$tmp/manifest"
mkdir -p "$manifest_dir/docs" "$manifest_dir/fixtures/v1/requirements" "$manifest_dir/schemas/v1" "$manifest_dir/tools"
cp "$root"/docs/specification.md "$root"/docs/implementation-plan.md "$root"/docs/open-questions.md "$manifest_dir/docs/"
cp "$root"/fixtures/v1/conformance.md "$manifest_dir/fixtures/v1/"
cp "$root"/schemas/v1/*.json "$manifest_dir/schemas/v1/"
cp "$root"/fixtures/v1/requirements/* "$manifest_dir/fixtures/v1/requirements/"
cp "$root"/tools/schema_check.py "$root"/tools/schema_check.py.lock "$manifest_dir/tools/"
(
  cd "$manifest_dir"
  git init -q
  git config user.email regression@example.invalid
  git config user.name regression
  git add .
  git commit -qm 'contract base'
  uv run --script --locked tools/schema_check.py manifest-write --manifest fixtures/v1/reference-manifest.json >write.out 2>&1
)
manifest="$manifest_dir/fixtures/v1/reference-manifest.json"
before=$(hash_file "$manifest")

printf '\n' >>"$manifest_dir/docs/specification.md"
if (cd "$manifest_dir" && uv run --script --locked tools/schema_check.py manifest-write --manifest fixtures/v1/reference-manifest.json >write.out 2>&1); then
  fail "dirty contract files: manifest-write unexpectedly succeeded"
fi
grep -q 'working tree differs' "$manifest_dir/write.out" || fail "dirty contract files: missing diagnostic"
after=$(hash_file "$manifest")
[ "$before" = "$after" ] || fail "dirty contract files: existing manifest was overwritten"
pass "dirty contract files: manifest-write fails before overwriting"

(
  cd "$manifest_dir"
  git add docs/specification.md
  git commit -qm 'contract change'
  uv run --script --locked tools/schema_check.py manifest-write --manifest fixtures/v1/reference-manifest.json --commit "$(git rev-parse HEAD)" >write2.out 2>&1
  uv run --script --locked tools/schema_check.py manifest-check --manifest fixtures/v1/reference-manifest.json >check2.out 2>&1
)
pass "documented order: commit contract files, then manifest-write and manifest-check"

for mutation in missing wrong-path wrong-sha; do
  case "$mutation" in
    missing)
      bad="$tmp/bad-missing.json"
      expected='requirements_source is required'
      python3 - "$manifest" "$bad" <<'PY'
import json, pathlib, sys
data = json.loads(pathlib.Path(sys.argv[1]).read_text())
del data["requirements_source"]
pathlib.Path(sys.argv[2]).write_text(json.dumps(data))
PY
      ;;
    wrong-path)
      bad="$tmp/bad-path.json"
      expected='requirements_source.path mismatch'
      python3 - "$manifest" "$bad" <<'PY'
import json, pathlib, sys
data = json.loads(pathlib.Path(sys.argv[1]).read_text())
data["requirements_source"]["path"] = "../missing.md"
pathlib.Path(sys.argv[2]).write_text(json.dumps(data))
PY
      ;;
    wrong-sha)
      bad="$tmp/bad-sha.json"
      expected='requirements_source.sha256 mismatch'
      python3 - "$manifest" "$bad" <<'PY'
import json, pathlib, sys
data = json.loads(pathlib.Path(sys.argv[1]).read_text())
data["requirements_source"]["sha256"] = "wrong"
pathlib.Path(sys.argv[2]).write_text(json.dumps(data))
PY
      ;;
  esac
  if (cd "$manifest_dir" && uv run --script --locked tools/schema_check.py manifest-check --manifest "$bad" >check.out 2>&1); then
    fail "manifest $mutation: manifest-check unexpectedly succeeded"
  fi
  grep -q "$expected" "$manifest_dir/check.out" || {
    cat "$manifest_dir/check.out" >&2
    fail "manifest $mutation: missing diagnostic $expected"
  }
  pass "manifest $mutation: manifest-check fails"
done

if ! sh "$root/tools/id07_semver.sh" >"$tmp/id07-pass.out" 2>&1; then
  cat "$tmp/id07-pass.out" >&2
  fail "ID-07 API check failed"
fi
grep -q 'ID-07 semver=7.7.4 first=true second=false' "$tmp/id07-pass.out" || fail "ID-07 version/result marker missing"
pass "ID-07 API: 7.7.4, first=true, second=false"

# 既存 node_modules があっても、現在の package.json/package-lock.json を使う。
mkdir -p "$tmp/id07-lock-missing/tools/id07/node_modules/semver"
cp "$root/tools/id07_semver.sh" "$tmp/id07-lock-missing/tools/"
cp "$root/tools/id07/package.json" "$root/tools/id07/check.mjs" "$tmp/id07-lock-missing/tools/id07/"
printf '%s\n' '{"name":"semver","version":"7.7.4","main":"index.js"}' >"$tmp/id07-lock-missing/tools/id07/node_modules/semver/package.json"
printf '%s\n' 'module.exports = { satisfies: () => true };' >"$tmp/id07-lock-missing/tools/id07/node_modules/semver/index.js"
set +e
sh "$tmp/id07-lock-missing/tools/id07_semver.sh" >"$tmp/id07-lock-missing.out" 2>&1
rc=$?
set -e
[ "$rc" -eq 2 ] || fail "ID-07 missing lock: expected exit 2, got $rc"
grep -q 'package-lock.json is missing' "$tmp/id07-lock-missing.out" || fail "ID-07 missing lock: missing diagnostic"
pass "ID-07 missing lock exits 2 even with node_modules"

mkdir -p "$tmp/id07-lock-inconsistent/tools/id07/node_modules/semver"
cp "$root/tools/id07_semver.sh" "$tmp/id07-lock-inconsistent/tools/"
cp "$root/tools/id07/package.json" "$root/tools/id07/package-lock.json" "$root/tools/id07/check.mjs" "$tmp/id07-lock-inconsistent/tools/id07/"
printf '%s\n' '{"name":"semver","version":"7.7.4","main":"index.js"}' >"$tmp/id07-lock-inconsistent/tools/id07/node_modules/semver/package.json"
printf '%s\n' 'module.exports = { satisfies: () => true };' >"$tmp/id07-lock-inconsistent/tools/id07/node_modules/semver/index.js"
python3 - "$tmp/id07-lock-inconsistent/tools/id07/package-lock.json" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
lock = json.loads(path.read_text())
lock["packages"]["node_modules/semver"]["version"] = "7.7.3"
path.write_text(json.dumps(lock))
PY
set +e
sh "$tmp/id07-lock-inconsistent/tools/id07_semver.sh" >"$tmp/id07-lock-inconsistent.out" 2>&1
rc=$?
set -e
[ "$rc" -eq 2 ] || fail "ID-07 inconsistent lock: expected exit 2, got $rc"
grep -q 'npm ci failed' "$tmp/id07-lock-inconsistent.out" || fail "ID-07 inconsistent lock: missing diagnostic"
pass "ID-07 inconsistent lock exits 2 even with node_modules"

mkdir -p "$tmp/id07-existing-node-modules/tools/id07/node_modules/semver"
cp "$root/tools/id07_semver.sh" "$tmp/id07-existing-node-modules/tools/"
cp "$root/tools/id07/package.json" "$root/tools/id07/package-lock.json" "$root/tools/id07/check.mjs" "$tmp/id07-existing-node-modules/tools/id07/"
printf '%s\n' '{"name":"semver","version":"7.7.3","main":"index.js"}' >"$tmp/id07-existing-node-modules/tools/id07/node_modules/semver/package.json"
printf '%s\n' 'module.exports = { satisfies: () => true };' >"$tmp/id07-existing-node-modules/tools/id07/node_modules/semver/index.js"
if ! sh "$tmp/id07-existing-node-modules/tools/id07_semver.sh" >"$tmp/id07-existing-node-modules.out" 2>&1; then
  cat "$tmp/id07-existing-node-modules.out" >&2
  fail "ID-07 existing node_modules: unexpected failure"
fi
grep -q 'ID-07 semver=7.7.4 first=true second=false' "$tmp/id07-existing-node-modules.out" || fail "ID-07 existing node_modules: lock-verified API did not run"
pass "ID-07 uses the lock-verified dependency, not existing node_modules"

mkdir -p "$tmp/fake-node"
real_node=$(command -v node)
cat >"$tmp/fake-node/node" <<EOF
#!/bin/sh
for arg in "\$@"; do
  case "\$arg" in
    */check.mjs|check.mjs) exit 1 ;;
  esac
done
exec "$real_node" "\$@"
EOF
chmod +x "$tmp/fake-node/node"
set +e
PATH="$tmp/fake-node:$PATH" sh "$root/tools/id07_semver.sh" >"$tmp/id07-node-fail.out" 2>&1
rc=$?
set -e
[ "$rc" -eq 2 ] || fail "ID-07 node startup failure: expected exit 2, got $rc"
grep -q 'API did not complete' "$tmp/id07-node-fail.out" || fail "ID-07 node startup failure: missing diagnostic"
pass "ID-07 node startup failure exits 2"

# Node は祖先ディレクトリの node_modules も探索するため、親に semver 7.7.4 の
# mock を置いた状態を再現条件として固定する。
mkdir -p "$tmp/node_modules/semver"
printf '%s\n' '{"name":"semver","version":"7.7.4","main":"index.js"}' >"$tmp/node_modules/semver/package.json"
printf '%s\n' 'module.exports = { satisfies: (version) => version === "1.9.0" };' >"$tmp/node_modules/semver/index.js"

mkdir -p "$tmp/id07-missing"
cp "$root/tools/id07/check.mjs" "$tmp/id07-missing/"
# 隔離前は親 mock が解決され、期待結果を返して exit 0 になることを確認する。
if ! node "$tmp/id07-missing/check.mjs" >"$tmp/id07-missing-parent.out" 2>&1; then
  cat "$tmp/id07-missing-parent.out" >&2
  fail "ID-07 missing dependency: parent mock was not resolved"
fi
grep -q '^ID-07 semver=7.7.4 first=true second=false$' "$tmp/id07-missing-parent.out" || {
  cat "$tmp/id07-missing-parent.out" >&2
  fail "ID-07 missing dependency: parent mock did not produce the expected result"
}

# check.mjs の隣の semver を exports で存在しないファイルへ向け、親 mock を
# 探索させずに依存欠落を再現する。missing.cjs は意図的に作成しない。
mkdir -p "$tmp/id07-missing/node_modules/semver"
printf '%s\n' '{"name":"semver","exports":"./missing.cjs"}' >"$tmp/id07-missing/node_modules/semver/package.json"
set +e
node "$tmp/id07-missing/check.mjs" >"$tmp/id07-missing.out" 2>&1
rc=$?
set -e
[ "$rc" -eq 2 ] || {
  cat "$tmp/id07-missing.out" >&2
  fail "ID-07 missing dependency: expected exit 2, got $rc"
}
grep -Eq "^FAIL ID-07 dependency: Cannot find module '.*[\\/]semver[\\/]missing\.cjs'$" "$tmp/id07-missing.out" || {
  cat "$tmp/id07-missing.out" >&2
  fail "ID-07 missing dependency: missing.cjs diagnostic"
}
pass "ID-07 missing dependency exits 2"

mkdir -p "$tmp/id07-wrong-result/node_modules/semver"
cp "$root/tools/id07/check.mjs" "$tmp/id07-wrong-result/"
printf '%s\n' '{"name":"semver","version":"7.7.4","main":"index.js"}' >"$tmp/id07-wrong-result/node_modules/semver/package.json"
printf '%s\n' 'module.exports = { satisfies: () => true };' >"$tmp/id07-wrong-result/node_modules/semver/index.js"
set +e
node "$tmp/id07-wrong-result/check.mjs" >"$tmp/id07-wrong-result.out" 2>&1
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "ID-07 wrong result: expected exit 1, got $rc"
grep -q 'FAIL ID-07 result' "$tmp/id07-wrong-result.out" || fail "ID-07 wrong result: missing diagnostic"
pass "ID-07 wrong result exits 1"

mkdir -p "$tmp/id07-wrong-version/node_modules/semver"
cp "$root/tools/id07/check.mjs" "$tmp/id07-wrong-version/"
printf '%s\n' '{"name":"semver","version":"7.7.3","main":"index.js"}' >"$tmp/id07-wrong-version/node_modules/semver/package.json"
printf '%s\n' 'module.exports = { satisfies: () => true };' >"$tmp/id07-wrong-version/node_modules/semver/index.js"
set +e
node "$tmp/id07-wrong-version/check.mjs" >"$tmp/id07-wrong-version.out" 2>&1
rc=$?
set -e
[ "$rc" -eq 2 ] || fail "ID-07 wrong version: expected exit 2, got $rc"
grep -q 'is not 7.7.4' "$tmp/id07-wrong-version.out" || fail "ID-07 wrong version: missing diagnostic"
pass "ID-07 wrong version exits 2"

echo "OK regression"
