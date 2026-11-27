# v1 スキーマ検証記録

2026-11-27 に CPython 3.13.18、`jsonschema[format]` 4.26.0、Draft 2020-12、`FormatChecker` を使って検証した。TOML は `tomllib` でパースし、版が TOML 上の整数であることを確認してから JSON と同じデータ構造を検証した。スキーマの相対参照はローカルの七ファイルを登録して解決した。

元の `requirements-2026-11-27.md` の SHA-256 は `749be3e73e2647b9f3fd658e4c5090c0b85435aef0a3112545c82f4d5368a045`。七つのコードブロックが [保存したサンプル](../fixtures/v1/requirements/) とバイト単位で一致することを確認した。

## 実行結果

```text
PASS meta-schema 7/7
PASS owner samples byte-for-byte 7/7
PASS nako.toml -> nako-manifest.schema.json
PASS METADATA.toml -> npkg-metadata.schema.json
PASS FILES.json -> npkg-files.schema.json
PASS COMMANDS.json -> npkg-commands.schema.json
PASS config.json -> sparse-index-config.schema.json
PASS package.json -> sparse-index-package.schema.json
PASS release.json -> publish-release.schema.json
PASS reject unknown manifest field (additionalProperties)
PASS reject unscoped ID (pattern)
PASS reject uppercase ID (pattern)
PASS reject double hyphen (pattern)
PASS reject public build metadata (pattern)
PASS reject GNU target without glibc (required)
PASS reject FILES lists itself (not)
PASS reject global flag mismatch (const)
PASS reject non-UTC date (pattern)
PASS reject HTTP artifact URL (pattern)
PASS reject no upload parts declared (minItems)
PASS reject uppercase SHA-256 (pattern)
OBSERVED sample mismatch: extra export in METADATA.toml: ./client
```

最後の行は二つのファイルに対するキー集合の比較結果。要件のサンプルには同一 ZIP 用に組み合わせると一致しない項目がある。`METADATA.toml` にだけ存在する `./client` はその一例で、§3.5 に従うとこの組み合わせは拒否される。 [差異の詳細](open-questions.md)

検証したのは個別のドキュメント構造と上記の比較。ZIP 実体、実サーバー、各ランタイムによる [適合性フィクスチャ](../fixtures/v1/conformance.md) の実行は実装時の作業となる。SPDX 式、SemVer Range の評価、ZIP や URL の配信元の検査も仕様本文の実行時の条件に含まれる。

## 再現手順

リポジトリルートで次のコマンドを実行する。親ディレクトリに元の要件ファイルがある場合はコードブロックとの一致も検査する。サンプル検証はリポジトリ内の入力だけで再現できる。

```sh
uv run --no-project --python 3.13.18 --with 'jsonschema[format]==4.26.0' python - <<'PY'
from copy import deepcopy
from pathlib import Path
import json
import re
import tomllib

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

schemas = Path("schemas/v1").resolve()
samples = Path("fixtures/v1/requirements")
pairs = {
    "nako.toml": "nako-manifest",
    "METADATA.toml": "npkg-metadata",
    "FILES.json": "npkg-files",
    "COMMANDS.json": "npkg-commands",
    "config.json": "sparse-index-config",
    "package.json": "sparse-index-package",
    "release.json": "publish-release",
}
assert {p.name for p in schemas.glob("*.schema.json")} == {
    f"{name}.schema.json" for name in pairs.values()
}
registry = Registry()
for path in sorted(schemas.glob("*.schema.json")):
    schema = json.loads(path.read_bytes())
    Draft202012Validator.check_schema(schema)
    registry = registry.with_resource(path.as_uri(), Resource.from_contents(schema))
print("PASS meta-schema 7/7")

source = Path("../requirements-2026-11-27.md")
if source.is_file():
    blocks = re.findall(rb"^```(?:toml|json)\n(.*?)^```$", source.read_bytes(), re.M | re.S)
    assert blocks == [(samples / filename).read_bytes() for filename in pairs]
    print("PASS owner samples byte-for-byte 7/7")

validators = {}
instances = {}
for filename, name in pairs.items():
    data = (samples / filename).read_bytes()
    if filename.endswith(".toml"):
        instance = tomllib.loads(data.decode("utf-8"))
        assert type(instance["schema_version"]) is int
    else:
        instance = json.loads(data)
    validator = Draft202012Validator(
        {"$ref": (schemas / f"{name}.schema.json").as_uri()},
        registry=registry,
        format_checker=FormatChecker(),
    )
    validator.validate(instance)
    validators[filename] = validator
    instances[filename] = instance
    print(f"PASS {filename} -> {name}.schema.json")

cases = [
    ("unknown manifest field", "nako.toml", (), "legacy", True, "additionalProperties"),
    ("unscoped ID", "nako.toml", ("package",), "id", "http", "pattern"),
    ("uppercase ID", "nako.toml", ("package",), "id", "@Std/pkg", "pattern"),
    ("double hyphen", "nako.toml", ("package",), "id", "@a--b/c", "pattern"),
    ("public build metadata", "release.json", (), "version", "1.2.0+rev", "pattern"),
    ("GNU target without glibc", "METADATA.toml", ("artifact", "native"), "glibc_min", None, "required"),
    ("FILES lists itself", "FILES.json", ("files", 2), "path", "NAKO-PKG/FILES.json", "not"),
    ("global flag mismatch", "COMMANDS.json", (), "exports_global_commands", False, "const"),
    ("non-UTC date", "package.json", (), "updated_at", "2026-11-27T13:30:00+09:00", "pattern"),
    ("HTTP artifact URL", "package.json", ("versions", 0, "artifacts", 0), "url", "http://cdn.example.invalid/a.npkg", "pattern"),
    ("no upload parts declared", "release.json", (), "uploaded_artifacts", [], "minItems"),
    ("uppercase SHA-256", "release.json", ("uploaded_artifacts", 0), "sha256", "sha256:" + "A" * 64, "pattern"),
]
for label, filename, location, name, value, keyword in cases:
    instance = deepcopy(instances[filename])
    parent = instance
    for part in location:
        parent = parent[part]
    if value is None:
        del parent[name]
    else:
        parent[name] = value
    errors = list(validators[filename].iter_errors(instance))
    assert any(error.validator == keyword for error in errors), (label, errors)
    print(f"PASS reject {label} ({keyword})")

metadata_exports = set(instances["METADATA.toml"]["exports"])
commands_exports = set(instances["COMMANDS.json"]["exports"])
assert metadata_exports - commands_exports == {"./client"}
assert not commands_exports - metadata_exports
print("OBSERVED sample mismatch: extra export in METADATA.toml: ./client")
PY

```
