#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.13.18"
# dependencies = [
#   "jsonschema[format]==4.26.0",
# ]
# ///
"""nako-registry v1 の schema・サンプル・TOML 写像を検証する常設ツール。

記録は docs/schema-validation.md、参照版は docs/schema-reference.md を参照。
相対 `$ref` は同じディレクトリのファイル URI だけを Registry に登録して解決し、
読み込みに失敗した場合は取得処理を一切呼ばずに失敗する。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tomllib
from copy import deepcopy
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker, validators
from referencing import Registry, Resource
from referencing.exceptions import PointerToNowhere

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = (ROOT / "schemas" / "v1").resolve()
SAMPLE_DIR = ROOT / "fixtures" / "v1" / "requirements"
CONFORMANCE = ROOT / "fixtures" / "v1" / "conformance.md"
MANIFEST_PATH = ROOT / "fixtures" / "v1" / "reference-manifest.json"
REQUIREMENTS_SOURCE = (ROOT.parent / "requirements-2026-11-27.md").resolve()

BASE_COMMIT = "af868c6976ab2d5432823c4341fbf27256d7a212"
REQUIREMENTS_SOURCE_REL = "../requirements-2026-11-27.md"
REQUIREMENTS_SOURCE_SHA256 = (
    "749be3e73e2647b9f3fd658e4c5090c0b85435aef0a3112545c82f4d5368a045"
)
MANIFEST_FORMAT = "nako-registry-reference/v1"

# ファイル名、schema 名、TOML かどうか。要件サンプルのコードブロック順。
PAIRS: tuple[tuple[str, str, bool], ...] = (
    ("nako.toml", "nako-manifest", True),
    ("METADATA.toml", "npkg-metadata", True),
    ("FILES.json", "npkg-files", False),
    ("COMMANDS.json", "npkg-commands", False),
    ("config.json", "sparse-index-config", False),
    ("package.json", "sparse-index-package", False),
    ("release.json", "publish-release", False),
)

DOC_PATHS: tuple[str, ...] = (
    "docs/specification.md",
    "docs/implementation-plan.md",
    "docs/open-questions.md",
)
FIXTURE_PATHS: tuple[str, ...] = ("fixtures/v1/conformance.md",)


class CheckFailure(RuntimeError):
    """検証結果が記録と一致しない。"""


class MappingFailure(ValueError):
    """TOML/JSON を JSON Schema の入力へ写像できない。"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _deny_retrieval(uri: str) -> Resource:
    raise CheckFailure(f"non-local $ref requires retrieval: {uri}")


def _strict_integer(_checker: Any, instance: Any) -> bool:
    # bool は int の派生なので型そのもので判定する。TOML の 1.0 も拒否する。
    return type(instance) is int


STRICT_INTEGER_VALIDATOR = validators.create(
    meta_schema=Draft202012Validator.META_SCHEMA,
    validators=Draft202012Validator.VALIDATORS,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
        "integer", _strict_integer
    ),
)


def _reject_json_constant(token: str) -> Any:
    raise MappingFailure(f"JSON non-finite number is not valid JSON: {token}")


def _child_path(path: str, key: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
        return f"{path}.{key}"
    return f"{path}[{json.dumps(key, ensure_ascii=False)}]"


def toml_to_json(value: Any, path: str) -> Any:
    """TOML の値を JSON のデータモデルへ写像する。

    int/float/bool はそのまま保持する。日時と非有限数は JSON に対応する値が
    ないため、schema 適用前に位置付きで拒否する。
    """
    if isinstance(value, dict):
        return {
            key: toml_to_json(child, _child_path(path, key))
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [toml_to_json(child, f"{path}[{index}]") for index, child in enumerate(value)]
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise MappingFailure(
                f"{path}: TOML non-finite float {value!r} has no JSON representation"
            )
        return value
    if isinstance(value, (datetime, date, time)):
        raise MappingFailure(
            f"{path}: TOML {type(value).__name__} {value!r} has no JSON representation"
        )
    raise MappingFailure(f"{path}: unsupported TOML value type {type(value).__name__}")


def parse_toml_bytes(data: bytes, origin: str) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MappingFailure(f"{origin}: not UTF-8: {exc}") from exc
    return parse_toml_text(text, origin)


def parse_toml_text(text: str, origin: str) -> Any:
    try:
        parsed = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise MappingFailure(f"{origin}: invalid TOML: {exc}") from exc
    mapped = toml_to_json(parsed, "$")
    if isinstance(mapped, dict) and "schema_version" in mapped:
        value = mapped["schema_version"]
        if type(value) is not int:
            raise MappingFailure(
                f"{origin}: $.schema_version must be a TOML integer (M-01), "
                f"got {type(value).__name__} {value!r}"
            )
    return mapped


def parse_json_bytes(data: bytes, origin: str) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MappingFailure(f"{origin}: not UTF-8: {exc}") from exc
    try:
        return json.loads(text, parse_constant=_reject_json_constant)
    except json.JSONDecodeError as exc:
        raise MappingFailure(f"{origin}: invalid JSON: {exc}") from exc


def load_instance(filename: str) -> Any:
    path = SAMPLE_DIR / filename
    if filename.endswith(".toml"):
        return parse_toml_bytes(path.read_bytes(), str(path))
    return parse_json_bytes(path.read_bytes(), str(path))


def _collect_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref":
                if not isinstance(child, str):
                    raise CheckFailure(f"$ref must be a string, got {type(child).__name__}")
                refs.append(child)
            else:
                refs.extend(_collect_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(_collect_refs(child))
    return refs


def _ref_error_detail(exc: Exception) -> str:
    if isinstance(exc, PointerToNowhere):
        return f"pointer not found: {exc.ref}"
    text = str(exc)
    return text if len(text) <= 300 else text[:297] + "..."


def _validate_resolved_schema(source: str, ref: str, contents: Any) -> None:
    if not isinstance(contents, (bool, dict)):
        raise CheckFailure(
            f"{source}: $ref {ref!r} resolves to {type(contents).__name__}, "
            "not a JSON Schema (boolean or object)"
        )
    try:
        Draft202012Validator.check_schema(contents)
    except Exception as exc:
        raise CheckFailure(
            f"{source}: $ref {ref!r} resolves to an invalid Draft 2020-12 schema: "
            f"{type(exc).__name__}: {_ref_error_detail(exc)}"
        ) from exc


def _resolve_all_refs(schemas: dict[str, dict[str, Any]], registry: Registry) -> tuple[int, int]:
    """サンプルが通る分岐に関係なく、全 `$ref` をローカルで解決・検証する。"""
    internal = 0
    file_refs = 0
    for _, name, _ in PAIRS:
        path = SCHEMA_DIR / f"{name}.schema.json"
        resolver = registry.resolver(base_uri=path.as_uri())
        try:
            refs = _collect_refs(schemas[name])
        except CheckFailure as exc:
            raise CheckFailure(f"{path.name}: {exc}") from exc
        for ref in refs:
            parsed = urlsplit(ref)
            if parsed.scheme or parsed.netloc or ref.startswith("//"):
                raise CheckFailure(f"{path.name}: remote $ref is not allowed: {ref}")
            try:
                resolved = resolver.lookup(ref)
            except Exception as exc:
                raise CheckFailure(
                    f"{path.name}: cannot resolve local $ref {ref!r}: "
                    f"{type(exc).__name__}: {_ref_error_detail(exc)}"
                ) from exc
            _validate_resolved_schema(path.name, ref, resolved.contents)
            if ref.startswith("#"):
                internal += 1
            else:
                file_refs += 1
    return internal, file_refs


def load_validators() -> dict[str, tuple[Any, Any]]:
    """schema を読み、JSON 用と TOML 用（厳密な整数）の validator を返す。"""
    expected = {f"{name}.schema.json" for _, name, _ in PAIRS}
    actual = {path.name for path in SCHEMA_DIR.glob("*.schema.json")}
    if actual != expected:
        raise CheckFailure(
            f"schema set mismatch: expected {sorted(expected)}, got {sorted(actual)}"
        )

    registry = Registry(retrieve=_deny_retrieval)
    schemas: dict[str, dict[str, Any]] = {}
    for _, name, _ in PAIRS:
        path = SCHEMA_DIR / f"{name}.schema.json"
        schema = json.loads(path.read_bytes(), parse_constant=_reject_json_constant)
        Draft202012Validator.check_schema(schema)
        schemas[name] = schema
        registry = registry.with_resource(path.as_uri(), Resource.from_contents(schema))

    internal, file_refs = _resolve_all_refs(schemas, registry)
    print(
        "PASS relative $ref only "
        f"({len(schemas)} schemas, {internal + file_refs} refs: "
        f"{internal} internal + {file_refs} file, 0 remote, all resolved)"
    )

    result: dict[str, tuple[Any, Any]] = {}
    for _, name, _ in PAIRS:
        uri = (SCHEMA_DIR / f"{name}.schema.json").as_uri()
        # `$ref` のラッパーを使うと子 validator が既定の type checker に戻るため、
        # `$id` を文書 URI に固定した schema 自体を直接適用する。
        validation_schema = dict(schemas[name])
        validation_schema.setdefault("$id", uri)
        result[name] = (
            Draft202012Validator(
                validation_schema, registry=registry, format_checker=FormatChecker()
            ),
            STRICT_INTEGER_VALIDATOR(
                validation_schema, registry=registry, format_checker=FormatChecker()
            ),
        )
    return result


def accept(label: str, validator: Any, instance: Any) -> int:
    errors = list(validator.iter_errors(instance))
    if errors:
        details = "; ".join(
            f"{list(error.absolute_path)}: {error.message}" for error in errors[:5]
        )
        raise CheckFailure(f"{label}: expected accept, got {len(errors)} error(s): {details}")
    print(f"PASS {label}")
    return 1


def reject(label: str, validator: Any, instance: Any, keyword: str) -> int:
    errors = list(validator.iter_errors(instance))
    if not any(error.validator == keyword for error in errors):
        found = sorted({str(error.validator) for error in errors}) or ["none"]
        raise CheckFailure(f"{label}: expected {keyword!r}, got {found}")
    print(f"PASS reject {label} ({keyword})")
    return 1


_MISSING = object()

REJECT_CASES: tuple[tuple[str, str, tuple[Any, ...], str, Any, str], ...] = (
    ("unknown manifest field", "nako.toml", (), "legacy", True, "additionalProperties"),
    ("unscoped ID", "nako.toml", ("package",), "id", "http", "pattern"),
    ("uppercase ID", "nako.toml", ("package",), "id", "@Std/pkg", "pattern"),
    ("double hyphen", "nako.toml", ("package",), "id", "@a--b/c", "pattern"),
    ("public build metadata", "release.json", (), "version", "1.2.0+rev", "pattern"),
    (
        "GNU target without glibc",
        "METADATA.toml",
        ("artifact", "native"),
        "glibc_min",
        _MISSING,
        "required",
    ),
    ("FILES lists itself", "FILES.json", ("files", 2), "path", "NAKO-PKG/FILES.json", "not"),
    ("global flag mismatch", "COMMANDS.json", (), "exports_global_commands", False, "const"),
    (
        "non-UTC date",
        "package.json",
        (),
        "updated_at",
        "2026-11-27T13:30:00+09:00",
        "pattern",
    ),
    (
        "HTTP artifact URL",
        "package.json",
        ("versions", 0, "artifacts", 0),
        "url",
        "http://cdn.example.invalid/a.npkg",
        "pattern",
    ),
    ("no upload parts declared", "release.json", (), "uploaded_artifacts", [], "minItems"),
    (
        "uppercase SHA-256",
        "release.json",
        ("uploaded_artifacts", 0),
        "sha256",
        "sha256:" + "A" * 64,
        "pattern",
    ),
    (
        "native-source without native table",
        "native-source variant",
        ("artifact",),
        "native",
        _MISSING,
        "required",
    ),
    (
        "native-source without ABI",
        "native-source variant",
        ("artifact", "native"),
        "abi_version",
        _MISSING,
        "required",
    ),
    (
        "invalid artifact entry path",
        "native-source variant",
        ("artifact", "entries"),
        ".",
        "/native/build.zig",
        "pattern",
    ),
    (
        "malformed dependency permission",
        "native-source variant",
        ("dependencies", 0),
        "allow_global_commands",
        "true",
        "type",
    ),
    (
        "yanked without reason",
        "yanked variant",
        ("versions", 0),
        "yank_reason",
        _MISSING,
        "required",
    ),
    (
        "yanked with blank reason",
        "yanked variant",
        ("versions", 0),
        "yank_reason",
        " ",
        "pattern",
    ),
)


CASE_SCHEMA = {
    "nako.toml": "nako-manifest",
    "METADATA.toml": "npkg-metadata",
    "FILES.json": "npkg-files",
    "COMMANDS.json": "npkg-commands",
    "config.json": "sparse-index-config",
    "package.json": "sparse-index-package",
    "release.json": "publish-release",
    "native-source variant": "npkg-metadata",
    "yanked variant": "sparse-index-package",
}


def _navigate(instance: Any, location: tuple[Any, ...]) -> Any:
    parent = instance
    for part in location:
        parent = parent[part]
    return parent


def _expect_mapping_failure(label: str, text: str, needle: str) -> int:
    try:
        parse_toml_text(text, label)
    except MappingFailure as exc:
        if needle not in str(exc):
            raise CheckFailure(f"{label}: expected {needle!r} in {exc}") from exc
        print(f"PASS reject {label} (TOML mapping: {needle})")
        return 1
    raise CheckFailure(f"{label}: expected a TOML mapping failure")


def run_checks(requirements_source: Path) -> int:
    print("nako-registry v1 schema check")
    print(f"root: {ROOT}")
    print()

    validators_by_schema = load_validators()
    json_validators = {name: pair[0] for name, pair in validators_by_schema.items()}
    toml_validators = {name: pair[1] for name, pair in validators_by_schema.items()}
    schemas_count = len(validators_by_schema)
    print(f"PASS meta-schema {schemas_count}/7")

    if requirements_source.is_file():
        digest = sha256_file(requirements_source)
        if digest != REQUIREMENTS_SOURCE_SHA256:
            raise CheckFailure(
                f"requirements source digest mismatch: {digest} != "
                f"{REQUIREMENTS_SOURCE_SHA256}"
            )
        blocks = re.findall(
            rb"^```(?:toml|json)\n(.*?)^```$",
            requirements_source.read_bytes(),
            re.M | re.S,
        )
        samples = [(SAMPLE_DIR / filename).read_bytes() for filename, _, _ in PAIRS]
        if blocks != samples:
            raise CheckFailure(
                "owner samples do not match the seven requirement code blocks "
                f"({len(blocks)} blocks, {len(samples)} samples)"
            )
        print(f"PASS owner samples byte-for-byte {len(samples)}/7")
    else:
        print(f"NOTE requirements source not found: {requirements_source}; byte check skipped")

    instances: dict[str, Any] = {}
    for filename, name, is_toml in PAIRS:
        instance = load_instance(filename)
        instance_json = json.loads(
            json.dumps(instance, ensure_ascii=False),
            parse_constant=_reject_json_constant,
        )
        validator = toml_validators[name] if is_toml else json_validators[name]
        accept(f"{filename} -> {name}.schema.json", validator, instance)
        # JSON 化できることを確認し、JSON 側の validator でも同じ結果になることを確かめる。
        accept(
            f"{filename} -> {name}.schema.json (JSON representation)",
            json_validators[name],
            instance_json,
        )
        instances[filename] = instance

    accepted = 0

    local_manifest = parse_toml_text("schema_version = 1\n[package]\n", "M-05 local")
    accepted += accept(
        "local-only manifest without publication fields (M-05 local)",
        toml_validators["nako-manifest"],
        local_manifest,
    )

    engines = deepcopy(instances["nako.toml"])
    engines["package"]["engines"]["lnako"] = ""
    accepted += accept(
        "empty range string (M-07)", toml_validators["nako-manifest"], engines
    )

    native_source = deepcopy(instances["METADATA.toml"])
    native_source["artifact"] = {
        "kind": "native-source",
        "runtimes": ["lnako"],
        "native": {"abi_version": 1},
        "entries": {".": "native/build.zig"},
    }
    native_source["dependencies"][0].update(
        alias="json_local", allow_global_commands=True
    )
    instances["native-source variant"] = native_source
    accepted += accept(
        "native-source ABI, artifact entries and dependency permissions",
        toml_validators["npkg-metadata"],
        native_source,
    )

    yanked = deepcopy(instances["package.json"])
    yanked["scope_id"] = "sc01"
    yanked["versions"][0].update(yanked=True, yank_reason="新版へ更新")
    instances["yanked variant"] = yanked
    accepted += accept(
        "opaque scope ID and yank reason", json_validators["sparse-index-package"], yanked
    )

    external_shape = deepcopy(instances["release.json"])
    external_shape["external_artifacts"] = [
        {
            "url": "https://repo.example.invalid/demo.npkg",
            "sha256": external_shape["uploaded_artifacts"][0]["sha256"],
        }
    ]
    accepted += accept(
        "external reference shape (publication disabled for initial deployment)",
        json_validators["publish-release"],
        external_shape,
    )

    binding_omitted = deepcopy(instances["nako.toml"])
    del binding_omitted["exports"]["."]["binding"]
    accepted += accept(
        "default export binding omitted (M-04)",
        toml_validators["nako-manifest"],
        binding_omitted,
    )

    nested_extension = deepcopy(instances["nako.toml"])
    nested_extension["package"]["release_notes"] = "初版"
    accepted += accept(
        "nested optional extension field (M-08)",
        toml_validators["nako-manifest"],
        nested_extension,
    )

    rejected = 0
    for label, filename, location, name, value, keyword in REJECT_CASES:
        instance = deepcopy(instances[filename])
        parent = _navigate(instance, location)
        if value is _MISSING:
            del parent[name]
        else:
            parent[name] = value
        validator = (
            toml_validators[CASE_SCHEMA[filename]]
            if filename in {"nako.toml", "METADATA.toml", "native-source variant"}
            else json_validators[CASE_SCHEMA[filename]]
        )
        rejected += reject(label, validator, instance, keyword)

    old_manifest = parse_toml_text(
        '[package]\nname = "demo"\nschema-version = 1\n', "M-06 old manifest"
    )
    rejected += reject(
        "M-06 old manifest missing top-level schema_version",
        toml_validators["nako-manifest"],
        old_manifest,
        "required",
    )

    toml_rejected = 0
    toml_rejected += _expect_mapping_failure(
        "M-01 schema_version = 1.0", "schema_version = 1.0\n[package]\n", "TOML integer"
    )
    toml_rejected += _expect_mapping_failure(
        "M-01 schema_version = true", "schema_version = true\n[package]\n", "TOML integer"
    )
    toml_rejected += _expect_mapping_failure(
        "TOML datetime",
        "schema_version = 1\n[package]\ndescription = 2026-11-27T13:30:00Z\n",
        "has no JSON representation",
    )
    toml_rejected += _expect_mapping_failure(
        "TOML infinity",
        "schema_version = 1\n[package]\nrelease_notes = inf\n",
        "non-finite",
    )
    toml_rejected += _expect_mapping_failure(
        "TOML NaN",
        "schema_version = 1\n[package]\nrelease_notes = nan\n",
        "non-finite",
    )

    abi_float = parse_toml_text(
        'schema_version = 1\n[package]\nid = "@soramikan/http"\n'
        'version = "1.2.0"\nlicense = "MIT"\n'
        "[artifacts.native]\nabi_version = 1.0\n",
        "TOML float abi_version",
    )
    toml_rejected += reject(
        "TOML float abi_version (integer required)",
        toml_validators["nako-manifest"],
        abi_float,
        "type",
    )

    metadata_exports = set(instances["METADATA.toml"]["exports"])
    commands_exports = set(instances["COMMANDS.json"]["exports"])
    if metadata_exports - commands_exports != {"./client"}:
        raise CheckFailure(
            "recorded sample mismatch changed: METADATA.toml minus COMMANDS.json is "
            f"{sorted(metadata_exports - commands_exports)}"
        )
    if commands_exports - metadata_exports:
        raise CheckFailure(
            "recorded sample mismatch changed: COMMANDS.json has extra "
            f"{sorted(commands_exports - metadata_exports)}"
        )
    print("OBSERVED sample mismatch: extra export in METADATA.toml: ./client")

    print()
    print("NOTE M-03 feature cycle: semantic validation is P02, not expressible in JSON Schema")
    print("NOTE M-05 pack-side id/version/license: P02; local structural case is covered")
    print("NOTE M-06 old-format diagnosis text: P02; only the structural rejection is covered")
    print("NOTE ID-07: node-semver 7.7.4 behavior is checked by tools/id07_semver.sh")
    print()
    print("SUMMARY")
    print(f"  meta-schema: {schemas_count}/7")
    print(f"  requirement samples: {len(PAIRS)}/7")
    print(f"  accepted structural variants: {accepted}")
    print(f"  rejected structural cases: {rejected} (18 recorded + M-06)")
    print(f"  TOML mapping/type rejections: {toml_rejected}")
    print("  observed sample mismatches: 1 (preserved, not fixed)")
    print("OK")
    return 0


def manifest_paths() -> list[str]:
    return [
        *DOC_PATHS,
        *FIXTURE_PATHS,
        *(f"schemas/v1/{name}.schema.json" for _, name, _ in PAIRS),
        *(f"fixtures/v1/requirements/{filename}" for filename, _, _ in PAIRS),
    ]


def _git_bytes(*args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def _git_commit_exists(commit: str) -> None:
    if not shutil.which("git"):
        raise CheckFailure("git is required to anchor a manifest to a commit")
    try:
        _git_bytes("cat-file", "-e", f"{commit}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise CheckFailure(f"commit is not available in this clone: {commit}") from exc


def _commit_blob(commit: str, path: str) -> bytes:
    try:
        return _git_bytes("show", f"{commit}:{path}")
    except subprocess.CalledProcessError as exc:
        raise CheckFailure(f"{path}: not present at commit {commit}") from exc


def build_manifest(commit: str) -> dict[str, Any]:
    """指定 commit の blob と作業ツリーの一致を確認して manifest を作る。

    契約ファイルを commit する前に生成すると、commit の内容と作業ツリーが
    食い違うため、既存 manifest を上書きする前に失敗する。
    """
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise CheckFailure(f"commit must be a full 40-character SHA-1: {commit!r}")
    _git_commit_exists(commit)

    entries: list[dict[str, str]] = []
    for path in manifest_paths():
        blob = _commit_blob(commit, path)
        blob_sha = sha256_bytes(blob)
        file_path = ROOT / path
        if not file_path.is_file():
            raise CheckFailure(f"{path}: working tree file is missing")
        working_sha = sha256_file(file_path)
        if working_sha != blob_sha:
            raise CheckFailure(
                f"{path}: working tree differs from {commit}; "
                "commit the contract files before manifest-write"
            )
        entries.append({"path": path, "sha256": blob_sha})

    if REQUIREMENTS_SOURCE.is_file():
        actual = sha256_file(REQUIREMENTS_SOURCE)
        if actual != REQUIREMENTS_SOURCE_SHA256:
            raise CheckFailure(
                f"requirements source digest changed: {actual} != "
                f"{REQUIREMENTS_SOURCE_SHA256}"
            )

    return {
        "format": MANIFEST_FORMAT,
        "commit": commit,
        "counts": {
            "documents": len(DOC_PATHS),
            "fixtures": len(FIXTURE_PATHS),
            "schemas": len(PAIRS),
            "samples": len(PAIRS),
        },
        "requirements_source": {
            "path": REQUIREMENTS_SOURCE_REL,
            "sha256": REQUIREMENTS_SOURCE_SHA256,
            "in_repository": False,
        },
        "files": entries,
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CheckFailure(f"manifest not found: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CheckFailure(f"manifest is not valid JSON: {exc}") from exc
    if manifest.get("format") != MANIFEST_FORMAT:
        raise CheckFailure(f"unexpected manifest format: {manifest.get('format')!r}")
    return manifest


def _require_requirements_metadata(manifest: dict[str, Any]) -> None:
    source = manifest.get("requirements_source")
    if not isinstance(source, dict):
        raise CheckFailure("manifest.requirements_source is required")
    if source.get("path") != REQUIREMENTS_SOURCE_REL:
        raise CheckFailure(
            "manifest.requirements_source.path mismatch: "
            f"{source.get('path')!r} != {REQUIREMENTS_SOURCE_REL!r}"
        )
    if source.get("sha256") != REQUIREMENTS_SOURCE_SHA256:
        raise CheckFailure(
            "manifest.requirements_source.sha256 mismatch: "
            f"{source.get('sha256')!r} != {REQUIREMENTS_SOURCE_SHA256!r}"
        )
    if source.get("in_repository") is not False:
        raise CheckFailure(
            "manifest.requirements_source.in_repository must be false"
        )


def manifest_check(path: Path) -> int:
    manifest = _load_manifest(path)
    _require_requirements_metadata(manifest)
    expected_paths = manifest_paths()
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise CheckFailure("manifest.files must be a list")
    paths = [entry.get("path") for entry in entries]
    if paths != expected_paths:
        raise CheckFailure(
            "manifest path order/content mismatch; "
            f"expected {len(expected_paths)} paths, got {len(paths)}"
        )

    for entry in entries:
        rel = entry["path"]
        expected = entry.get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise CheckFailure(f"{rel}: invalid sha256 in manifest")
        file_path = ROOT / rel
        if not file_path.is_file():
            raise CheckFailure(f"manifest file missing: {rel}")
        actual = sha256_file(file_path)
        if actual != expected:
            raise CheckFailure(f"{rel}: sha256 mismatch {actual} != {expected}")
    print(f"PASS manifest working tree {len(entries)}/{len(expected_paths)}")
    print("PASS manifest requirements metadata path and sha256")

    commit = manifest.get("commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise CheckFailure(f"manifest commit is invalid: {commit!r}")
    if shutil.which("git"):
        try:
            _git_bytes("cat-file", "-e", f"{commit}^{{commit}}")
        except subprocess.CalledProcessError as exc:
            raise CheckFailure(
                f"manifest commit is not available in this clone: {commit}"
            ) from exc
        for entry in entries:
            blob = _git_bytes("show", f"{commit}:{entry['path']}")
            actual = sha256_bytes(blob)
            if actual != entry["sha256"]:
                raise CheckFailure(
                    f"{entry['path']}: bytes at {commit} differ from manifest "
                    f"({actual} != {entry['sha256']})"
                )
        print(f"PASS manifest commit anchor {len(entries)}/{len(entries)} at {commit}")
    else:
        print("NOTE git not found; commit anchor skipped, file digests still checked")

    if REQUIREMENTS_SOURCE.is_file():
        actual = sha256_file(REQUIREMENTS_SOURCE)
        if actual != REQUIREMENTS_SOURCE_SHA256:
            raise CheckFailure(
                f"requirements source digest mismatch: {actual} != "
                f"{REQUIREMENTS_SOURCE_SHA256}"
            )
        print(f"PASS requirements source {REQUIREMENTS_SOURCE_REL}")
    else:
        print(
            f"NOTE requirements source {REQUIREMENTS_SOURCE_REL} not present; "
            "metadata verified, byte check skipped"
        )
    print("OK")
    return 0


def manifest_write(path: Path, commit: str | None) -> int:
    if commit is None:
        if not shutil.which("git"):
            raise CheckFailure("--commit is required when git is unavailable")
        commit = _git_bytes("rev-parse", "HEAD").decode("ascii").strip()
    # 生成と作業ツリー照合がすべて成功するまで既存ファイルへ書き込まない。
    manifest = build_manifest(commit)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    try:
        display = path.relative_to(ROOT)
    except ValueError:
        display = path
    print(f"WROTE {display} ({len(manifest['files'])} files, {commit})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="schema_check.py",
        description="nako-registry v1 の schema・サンプル・TOML 写像を検証する",
    )
    sub = parser.add_subparsers(dest="command")
    check = sub.add_parser("check", help="schema、サンプル、受理例、拒否例を検証する")
    check.add_argument(
        "--requirements-source",
        type=Path,
        default=None,
        help="原本 requirements-2026-11-27.md（省略時は親ディレクトリ）",
    )
    manifest_check_parser = sub.add_parser("manifest-check", help="参照 manifest を照合する")
    manifest_check_parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    manifest_write_parser = sub.add_parser("manifest-write", help="参照 manifest を再生成する")
    manifest_write_parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    manifest_write_parser.add_argument("--commit", default=None)

    args = parser.parse_args(argv)
    try:
        if args.command == "manifest-check":
            return manifest_check(args.manifest.resolve())
        if args.command == "manifest-write":
            return manifest_write(args.manifest.resolve(), args.commit)
        source = getattr(args, "requirements_source", None) or REQUIREMENTS_SOURCE
        return run_checks(source.resolve())
    except (CheckFailure, MappingFailure) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
