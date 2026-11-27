# v1 参照版の固定

別の処理系が同じ仕様・schema・適合性フィクスチャを参照するための固定点。値はリポジトリ内の実データから生成し、特定の処理系に依存しない。

| 項目 | 値 |
| --- | --- |
| リポジトリ | `nako-registry` |
| 固定 commit | `af868c6976ab2d5432823c4341fbf27256d7a212` |
| manifest | [`fixtures/v1/reference-manifest.json`](../fixtures/v1/reference-manifest.json) |
| manifest format | `nako-registry-reference/v1` |
| 収録数 | 仕様 3、適合性フィクスチャ 1、schema 7、サンプル 7（計 18） |

manifest の `files[]` は各ファイルのリポジトリ相対パスと SHA-256 を持つ。`commit` は契約ファイルを含む commit で、全 18 ファイルのバイト列がその blob と一致することを `manifest-check` が確認する。

## 収録するファイル

- 仕様: `docs/specification.md`、`docs/implementation-plan.md`、`docs/open-questions.md`
- 適合性フィクスチャ: `fixtures/v1/conformance.md`
- JSON Schema 7 件: `schemas/v1/*.schema.json`
- 要件サンプル 7 件: `fixtures/v1/requirements/`（`nako.toml`、`METADATA.toml`、`FILES.json`、`COMMANDS.json`、`config.json`、`package.json`、`release.json`）

要件原本 `../requirements-2026-11-27.md` はリポジトリ外にある。manifest には `requirements_source` としてパスと SHA-256 `749be3e73e2647b9f3fd658e4c5090c0b85435aef0a3112545c82f4d5368a045` を必須で記録する。`manifest-check` は原本の有無にかかわらずこのメタデータを v1 の記録と照合し、原本がある場合だけバイトを照合する。原本がない場合はメタデータを確認した上で `NOTE` を出し、七サンプルの検証は続ける。

## 検証

リポジトリルートで実行する。

```sh
uv run --script --locked tools/schema_check.py manifest-check
```

成功時の出力:

```text
PASS manifest working tree 18/18
PASS manifest requirements metadata path and sha256
PASS manifest commit anchor 18/18 at af868c6976ab2d5432823c4341fbf27256d7a212
PASS requirements source ../requirements-2026-11-27.md
OK
```

`manifest-check` は次を行う。

1. manifest の `format` と `files[]` のパス集合・順序を確認する。
2. `requirements_source` のパス・SHA-256・`in_repository = false` を v1 の記録と照合する。項目の欠落や不一致は失敗する。
3. 作業ツリーの各ファイルの SHA-256 を `files[].sha256` と照合する。
4. git がある場合、`commit` の存在を確認し、`git show <commit>:<path>` のバイト列を各 `sha256` と照合する。
5. リポジトリ外の要件原本がある場合だけ、記録した SHA-256 を照合する。ない場合は `NOTE` を出して 4 までの確認を続ける。

git がない環境や shallow clone で commit が取得できない場合、commit の照合はできない。その場合も作業ツリーのダイジェスト照合は有効だが、manifest が指す固定点としては不十分なので、`git fetch` などで commit を取得する。git があるのに commit を取得できない場合、`manifest-check` は失敗する。要件原本がないことは失敗ではなく、`requirements_source` のメタデータ検査だけは常に必須である。ダイジェストだけを手動で確認する場合は、macOS なら `shasum -a 256`、Linux なら `sha256sum` を使う。

```sh
shasum -a 256 docs/specification.md fixtures/v1/conformance.md schemas/v1/*.schema.json fixtures/v1/requirements/*
```

## 別処理系からの参照手順

1. manifest を取得し、`format` が `nako-registry-reference/v1` であることを確認する。
2. `files[]` の各 `path` を読み、`sha256` を照合する。パスは manifest を持つリポジトリのルートからの相対パス。
3. 可能なら `commit` の blob とも照合する。digest だけでも内容は固定できるが、commit はスキーマ・サンプル・仕様の来歴を示す。
4. schema は Draft 2020-12 として読み込む。相対 `$ref` は同じ `schemas/v1/` ディレクトリのファイルとして解決し、ネットワーク取得に頼らない。
5. TOML の二つの入力は、[スキーマ検証記録](schema-validation.md#toml-から-json-への写像) の規則で JSON のデータモデルへ写す。特に `schema_version` は TOML の整数だけを受理し、`1.0` と `true` を拒否する。
6. `fixtures/v1/requirements/` のサンプルは単体の構造例であり、同一 ZIP の制御ファイルとして組み合わせない。`METADATA.toml` の `./client` が `COMMANDS.json` にない差異は記録済みで、修正しない。組み合わせた適合性入力は `fixtures/v1/conformance.md` の Z0 を使う。
7. ID-07 の範囲判定は `node-semver` 7.7.4 の API を基準にする。[`tools/id07/check.mjs`](../tools/id07/check.mjs) が一度の Node 実行で 2 ケースを照合する。入口の [`tools/id07_semver.sh`](../tools/id07_semver.sh) は現在の `package.json` と `package-lock.json` を一時ディレクトリへコピーし、`npm ci --ignore-scripts` を毎回実行してから起動する。既存の `node_modules` は使わない。ロックの欠落・不整合、依存の導入・起動・版・判定処理の失敗は exit 2、判定結果の不一致は exit 1 とする。

## manifest の更新

契約ファイル（仕様、適合性フィクスチャ、schema、サンプル）を変更した場合、manifest を変更前の commit に混ぜない。次の順で更新する。

1. 契約ファイルを変更し、レビューして commit する。この commit を C とする。
2. C の作業ツリーで manifest を生成する。

   ```sh
   uv run --script --locked tools/schema_check.py manifest-write --commit <C>
   ```

   `manifest-write` は C の blob と作業ツリーの全 18 ファイルを照合する。一致しない場合は既存 manifest を上書きせずに失敗する。`--commit` を省略した場合は HEAD を使う。
3. 生成した manifest を照合する。

   ```sh
   uv run --script --locked tools/schema_check.py manifest-check
   ```

   `manifest-check` は作業ツリー、C の blob、`requirements_source` を確認する。
4. 生成した manifest とこの文書の固定 commit 欄を更新し、別 commit で記録する。

`--manifest` でリポジトリ外のパスを指定した場合も、`WROTE` の表示はそのパスになる。異常系は [`tools/regression_schema_check.sh`](../tools/regression_schema_check.sh) で確認できる。
