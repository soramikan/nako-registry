# v1 スキーマ検証記録

2026-11-27 に CPython 3.13.18、`jsonschema[format]` 4.26.0、Draft 2020-12、`FormatChecker` を使って検証した。TOML は `tomllib` でパースし、版が TOML 上の整数であることを確認してから JSON と同じデータ構造を検証した。スキーマの相対参照はローカルの七ファイルを登録して解決した。

元の `requirements-2026-11-27.md` の SHA-256 は `749be3e73e2647b9f3fd658e4c5090c0b85435aef0a3112545c82f4d5368a045`。七つのコードブロックが [保存したサンプル](../fixtures/v1/requirements/) とバイト単位で一致することを確認した。

再現用スクリプトは 2026-11-28 に [常設ツール](../tools/schema_check.py) へ移した。依存は PEP 723 のインラインメタデータと `tools/schema_check.py.lock` で固定する。固定した参照版は [参照版の固定](schema-reference.md) を参照。

## 実行結果（2026-11-27 の記録）

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
PASS local-only manifest without publication fields
PASS empty range string
PASS native-source ABI, artifact entries and dependency permissions
PASS opaque scope ID and yank reason
PASS external reference shape (publication disabled for initial deployment)
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
PASS reject native-source without native table (required)
PASS reject native-source without ABI (required)
PASS reject invalid artifact entry path (pattern)
PASS reject malformed dependency permission (type)
PASS reject yanked without reason (required)
PASS reject yanked with blank reason (pattern)
OBSERVED sample mismatch: extra export in METADATA.toml: ./client
```

最後の行は二つのファイルに対するキー集合の比較結果。要件のサンプルには同一 ZIP 用に組み合わせると一致しない項目がある。`METADATA.toml` にだけ存在する `./client` はその一例で、§3.5 に従うとこの組み合わせは拒否される。 [差異の詳細](open-questions.md)

スキーマ検証では原文の7件と追加の受理例5件が通り、拒否例18件が期待どおり失敗した。外部参照は共通スキーマの構造を検証した。初版のサーバーは値のある `external_artifacts` を公開ポリシーで拒否する。

範囲判定 ID-07 は `node-semver` 7.7.4 の CLI でも実行した。`1.9.0` は適合し、caret 上限の `2.0.0-alpha.2` は不適合（終了コード1）。各処理系の実装、ZIP 実体、実サーバーを使う [適合性フィクスチャ](../fixtures/v1/conformance.md) は実装時に実行する。

## 常設ツールによる再検証（2026-11-28）

`tools/schema_check.py` の `check` は、次の件数を一件ずつ検証する。固定した入力だけを使い、親ディレクトリの原本がある場合はサンプルとのバイト一致も確認する。

```sh
uv run --script --locked tools/schema_check.py check
uv run --script --locked tools/schema_check.py manifest-check
```

再実行した結果:

```text
PASS relative $ref only (7 schemas, 74 refs: 36 internal + 38 file, 0 remote, all resolved)
PASS meta-schema 7/7
PASS owner samples byte-for-byte 7/7
PASS nako.toml -> nako-manifest.schema.json
PASS nako.toml -> nako-manifest.schema.json (JSON representation)
PASS METADATA.toml -> npkg-metadata.schema.json
PASS METADATA.toml -> npkg-metadata.schema.json (JSON representation)
PASS FILES.json -> npkg-files.schema.json
PASS FILES.json -> npkg-files.schema.json (JSON representation)
PASS COMMANDS.json -> npkg-commands.schema.json
PASS COMMANDS.json -> npkg-commands.schema.json (JSON representation)
PASS config.json -> sparse-index-config.schema.json
PASS config.json -> sparse-index-config.schema.json (JSON representation)
PASS package.json -> sparse-index-package.schema.json
PASS package.json -> sparse-index-package.schema.json (JSON representation)
PASS release.json -> publish-release.schema.json
PASS release.json -> publish-release.schema.json (JSON representation)
PASS local-only manifest without publication fields (M-05 local)
PASS empty range string (M-07)
PASS native-source ABI, artifact entries and dependency permissions
PASS opaque scope ID and yank reason
PASS external reference shape (publication disabled for initial deployment)
PASS default export binding omitted (M-04)
PASS nested optional extension field (M-08)
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
PASS reject native-source without native table (required)
PASS reject native-source without ABI (required)
PASS reject invalid artifact entry path (pattern)
PASS reject malformed dependency permission (type)
PASS reject yanked without reason (required)
PASS reject yanked with blank reason (pattern)
PASS reject M-06 old manifest missing top-level schema_version (required)
PASS reject M-01 schema_version = 1.0 (TOML mapping: TOML integer)
PASS reject M-01 schema_version = true (TOML mapping: TOML integer)
PASS reject TOML datetime (TOML mapping: has no JSON representation)
PASS reject TOML infinity (TOML mapping: non-finite)
PASS reject TOML NaN (TOML mapping: non-finite)
PASS reject TOML float abi_version (integer required) (type)
OBSERVED sample mismatch: extra export in METADATA.toml: ./client

NOTE M-03 feature cycle: semantic validation is P02, not expressible in JSON Schema
NOTE M-05 pack-side id/version/license: P02; local structural case is covered
NOTE M-06 old-format diagnosis text: P02; only the structural rejection is covered
NOTE ID-07: node-semver 7.7.4 behavior is checked by tools/id07_semver.sh

SUMMARY
  meta-schema: 7/7
  requirement samples: 7/7
  accepted structural variants: 7
  rejected structural cases: 19 (18 recorded + M-06)
  TOML mapping/type rejections: 6
  observed sample mismatches: 1 (preserved, not fixed)
OK
```

### TOML から JSON への写像

`tomllib` の値を JSON Schema の入力へ写すとき、次の規則を使う。

- `schema_version` は TOML の整数（`int`）だけを受理する。`1.0` は float、`true` は bool であり、どちらも [M-01](../fixtures/v1/conformance.md) として拒否する。JSON Schema の数値等価だけでは `1.0` と `1` を区別できないため、写像前にトップレベルを検査する。
- それ以外の TOML の `int`、`float`、`bool` は型を保持する。TOML 由来の入力には `type: integer` を `int` だけに一致させる validator を使うため、`artifacts.native.abi_version = 1.0` のような float も拒否する。
- TOML の日時（offset/localtime の datetime、date、time）は JSON に対応する値がないため、位置付きで拒否する。
- TOML の `inf`、`-inf`、`nan` は JSON の数値ではないため拒否する。JSON 入力の `NaN`、`Infinity`、`-Infinity` も `parse_constant` で拒否する（個別件数には含めない）。
- JSON に写した TOML サンプルは、通常の JSON 用 validator でも同じ結果になることを確認する。受理例・拒否例は TOML 用 validator を使う。

### 相対 `$ref` のオフライン解決

七つの schema は同じディレクトリのファイルと `#/$defs/...` だけを参照する。ツールは各 schema をファイル URI で `referencing.Registry` に登録し、文書の `$id` をその URI に固定して適用する。`Registry` の取得処理は例外を返すようにしてあり、未登録の参照やネットワーク取得が必要な参照は成功扱いにしない。`jsonschema.RefResolver` は使わない。

参照検査はインスタンス検証とは独立している。全 74 参照（同一文書 36、ファイル間 38）を、サンプルが通る分岐に関係なく `resolver.lookup` でフラグメントまで解決する。存在しない内部参照先・ファイル間参照先、外部参照は、参照元の schema ファイル名と参照文字列を付けて非ゼロ終了にする。

解決結果の `contents` も検査する。boolean または object であること、Draft 2020-12 のメタスキーマで有効な schema であることを確認する。文字列・数値・配列など schema でない値を指す参照は、参照元と参照文字列を付けて拒否する。現行の 74 参照はすべてこの検査を通る。

### 記録したサンプル差異

`fixtures/v1/requirements/` の七サンプルは変更していない。`METADATA.toml` の `./client` が `COMMANDS.json` にない差異は、要件どおり「単体の構造例」として保持し、ツールはこの差異を `OBSERVED` として報告する。文字列・ケースの修正は行わない。同一 ZIP 用の入力は [適合性フィクスチャ](../fixtures/v1/conformance.md) の Z0 を使う。

### M-01〜M-08 の扱い

P01 は schema で判定できる構造だけを対象にし、意味検証は P02 に渡す。

| ケース | このツールでの扱い |
| --- | --- |
| M-01 | `schema_version = 1.0` と `true` を拒否する。TOML の整数だけを受理。 |
| M-02 | 未知のトップレベルキーを `additionalProperties` で拒否する。 |
| M-03 | feature の循環は schema で表現できない。P02 の意味検証。 |
| M-04 | `exports["."].binding` の省略を受理する。 |
| M-05 | ローカルの `schema_version = 1` と空の `[package]` を受理する。配布用の `id`・`version`・`license` 必須は P02。 |
| M-06 | 旧 `[package]` の `name` と `schema-version` はトップレベル `schema_version` を欠くため拒否する。旧形式の診断文と暗黙変換の禁止は P02。 |
| M-07 | `package.engines.lnako` の空文字列を構造として受理する。 |
| M-08 | `package.release_notes` のような入れ子の任意拡張を受理する。 |

ID-01〜ID-06 の識別子・公開バージョンの判定は P02 の実装で検証する。ID-07 は次の範囲判定で確認する。

## 範囲判定 ID-07

`node-semver` 7.7.4 の API を、`tools/id07/check.mjs` が一度の Node 実行で照合する。`tools/id07_semver.sh` は毎回 `mktemp` のディレクトリへ `package.json`、`package-lock.json`、`check.mjs` をコピーし、そのディレクトリで `npm ci --ignore-scripts` を一度実行してから `node check.mjs` を起動する。既存の `tools/id07/node_modules` は使わない。

`check.mjs` は `semver/package.json` の版が 7.7.4 であること、`satisfies` が前半 true・後半 false であることを確認する。`loose` と `includePrerelease` は明示的に無効にする。ロックが欠落している場合や `package.json` と不整合な場合は `npm ci` が失敗し、導入済みの `node_modules` があっても成功にしない。

依存の導入・起動・版・判定処理の失敗は exit 2、判定結果の不一致は exit 1 とする。`id07_semver.sh` は Node の出力を検査し、`ID-07 semver=7.7.4` と 2 つの `PASS` がそろわない成功終了も dependency failure として扱う。npm の実行失敗を「範囲に不適合」と誤認しない。

```sh
sh tools/id07_semver.sh
```

実行結果:

```text
ID-07 semver=7.7.4 first=true second=false
PASS ID-07 1.9.0 satisfies ^1.2.3
PASS ID-07 2.0.0-alpha.2 rejected by ^1.2.3 >=2.0.0-alpha.1 (caret upper bound)
```

`1.9.0` は `^1.2.3` に適合し、`2.0.0-alpha.2` は `^1.2.3 >=2.0.0-alpha.1` に不適合である。後者は caret の上限 `<2.0.0-0` も満たさない。

## 異常系の回帰確認

`sh tools/regression_schema_check.sh` は一時コピーだけで次を確認する。

- サンプルが通らない分岐の壊れた内部 `$ref`、存在しないファイル間 `$ref`、外部 `$ref` を非ゼロ終了にする。
- 参照先が文字列・数値・配列の非 schema を拒否し、boolean schema を受理する。
- 契約ファイルが commit と一致しないとき、`manifest-write` が既存 manifest を上書きする前に失敗する。
- 契約ファイルを commit した後、`manifest-write` と `manifest-check` が通る。
- `requirements_source` の欠落、パス不一致、SHA-256 不一致を拒否する。
- `package-lock.json` の欠落・不整合を、既存 `node_modules` があっても拒否する。
- 既存 `node_modules` と異なる固定依存を一時導入し、ロック検証済みの 7.7.4 で実行する。
- ID-07 の依存欠落を exit 2、判定結果の不一致を exit 1 として区別する。
- 実 API の 7.7.4 で前半 true・後半 false を確認する。

実行結果は 20 行の `PASS` と `OK regression`。詳細はスクリプトを参照。

## 再現手順

リポジトリルートで次を実行する。`--locked` は `tools/schema_check.py.lock` とインラインメタデータの解決結果が一致しない場合に失敗する。

```sh
uv run --script --locked tools/schema_check.py check
uv run --script --locked tools/schema_check.py manifest-check
sh tools/id07_semver.sh
sh tools/regression_schema_check.sh
```

依存を更新する場合だけ、ロックを作り直して差分を確認する。

```sh
uv lock --script tools/schema_check.py
```

`check` は親ディレクトリの `../requirements-2026-11-27.md` があれば、記録した SHA-256 と七つのコードブロックのバイト一致を確認する。原本がない環境ではこの確認だけを `NOTE` として飛ばし、リポジトリ内の七サンプルは検証する。`manifest-check` の詳細は [参照版の固定](schema-reference.md) を参照。

uv の既定キャッシュに書き込めない環境では、`UV_CACHE_DIR` を書き込み可能なディレクトリにするか、`uv run --no-cache --script --locked tools/schema_check.py check` を使う。`--locked` はどちらの場合も維持する。
