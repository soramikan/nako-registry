# なでしこパッケージ形式・レジストリ仕様 v1

適用範囲は `lnako`、`cnako`、`wnako`、`nako-registry`。本文の節番号は「パッケージ形式・レジストリ仕様 要件（2026-11-27 みかん提示）」の §1〜§7 に対応する。旧仕様や Issue の記述と食い違う場合、この版では同日付の要件に従う。要件で値や挙動を確定できない箇所は [未決定事項](open-questions.md) に記載する。

`MUST` と `MUST NOT` は必須と禁止、`SHOULD` は推奨、`MAY` は任意を表す。 [RFC 2119](https://www.rfc-editor.org/info/rfc2119/)

## 1. 共通規約・識別子・基本型

### 1.1 パッケージ識別子

レジストリ上の Package ID は `@{scope}/{name}` を使う（MUST）。`scope` は `^[a-z][a-z0-9-]{1,38}$`、`name` は `^[a-z][a-z0-9-]{0,63}$` にそれぞれ文字列全体が一致しなければならない（MUST）。どちらも末尾の `-` と連続する `--` を拒否する（MUST）。大文字を含む入力は拒否し、検証済みの小文字表現で比較、保存、URL 生成を行う（MUST）。

一般利用者による `std`、`nako`、`nadesiko`、`nadesiko3`、`lnako`、`cnako`、`wnako`、`core`、`official`、`registry`、`system`、`internal` の登録を拒否する（MUST）。予約判定は一般登録の権限検査で行う。たとえば `@std/json` は依存の ID として構文上有効であり、参照先の存在は別途確認する。

### 1.2 バージョン・ハッシュ・日時・ターゲット

| 値 | 要件 |
| --- | --- |
| バージョン | SemVer 2.0.0 に厳格に従う（MUST）。公開バージョン文字列にビルドメタデータ `+...` を含めてはならない（MUST NOT）。 |
| ハッシュ | `sha256:` に小文字16進数64桁を続ける（MUST）。 |
| 日時 | UTC の RFC 3339 を使う（MUST）。例は `2026-11-27T13:30:00Z`。 |
| `runtime` | `lnako`、`cnako`、`wnako` のいずれか（MUST）。 |
| `target_triple` | LLVM/Zig 準拠の `{arch}-{os}-{abi}`（MUST）。例は `aarch64-macos-none`、`x86_64-linux-gnu`、`x86_64-linux-musl`、`x86_64-windows-msvc`。 |
| `capabilities` | `pure-nako`、`native`、`ffi`、`fs`、`net`、`env`、`process`、`unsafe` から宣言する（MUST）。純粋ななでしこの宣言例は `["pure-nako"]`。 |

公開バージョンと範囲式は用途が異なる。範囲式は依存や engine の適合判定に使う。範囲式の完全な文法は [O04](open-questions.md#o04) を参照。 [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html) / [RFC 3339](https://www.rfc-editor.org/info/rfc3339/)

| `artifact_kind` | 内容と対象 |
| --- | --- |
| `universal` | 純粋な `.nako3` ソースと共通定義。全ランタイム共通。 |
| `esm` | ビルド済みの JavaScript または TypeScript の ESM。対象は `cnako`、`wnako`、または双方。 |
| `native-source` | Zig、C、CMake などのビルド用ソース。`lnako` のフォールバック。 |
| `native-prebuilt` | 特定ターゲット向けのビルド済みネイティブライブラリ。`lnako` 用。 |

## 2. プロジェクトの `nako.toml`

開発者はリポジトリルートにソースマニフェストを置く。要件 §2.1 の [サンプル](../fixtures/v1/requirements/nako.toml) と [スキーマ](../schemas/v1/nako-manifest.schema.json) を参照。

| キー | 構造 |
| --- | --- |
| `schema_version` | トップレベルの整数 `1`（MUST）。 |
| `package` | 公開時は `id`、`version`、`license`（SPDX 式）が必須（MUST）。説明、配布元リポジトリ、ホームページ、README のパス、キーワード、capabilities を記述できる。 |
| `package.engines` | ランタイム名から対応する SemVer Range への表。 |
| `exports` | `.` が既定の入口、`./client` のようなキーが公開サブパス。各値は `entry` と任意の `binding` を持つ。 |
| `features` | feature 名から追加で有効にする feature の配列への表。`default` に既定の feature 群を記述できる。 |
| `artifacts.universal` | `include` に収録対象を記述する。 |
| `artifacts.esm` | `runtimes`、`entry`、`include` に ESM の配布対象を記述する。 |
| `artifacts.native` | `abi_version`、`source_include`、`prebuilt_lib_name` にソースとビルド済みライブラリの組み立て情報を記述する。 |
| `dependencies`、`runtime-dependencies.<runtime>`、`dev-dependencies` | キーは完全修飾 Package ID。値はバージョン範囲の文字列か、`version` と任意の `alias`、`features`、`allow_global_commands` を持つ表。 |
| `profiles.<profile>` | `runtime` に解決対象のランタイムを記述する。`default` はプロファイル名の例。 |

未知のトップレベルキーを拒否する（MUST）。TOML の `schema_version = 1.0` は整数 `1` と区別する（MUST）。`binding` の省略は `scoped` と扱い、`global` が一つでもあれば `exports_global_commands = true` と判定する（MUST）。ローカル解決名の重複はビルドまたは解決時に検査する（MUST、§6.1）。feature は加算的で、循環参照を拒否する（MUST）。 [SPDX 式](https://spdx.github.io/spdx-spec/v2.3.1/SPDX-license-expressions/)

## 3. `.npkg` 配布アーカイブ

論理バージョンを一つ以上の `.npkg` で配布する（MUST）。各 `.npkg` は種別と対象に対応する単一アーティファクトを表す。

### 3.1 ファイル名

ファイル名は次の形を使うことを推奨する（SHOULD）。

| 種別 | ファイル名 |
| --- | --- |
| Universal | `{scope}__{name}-{version}-universal.npkg` |
| ESM | `{scope}__{name}-{version}-esm-{runtime_tag}.npkg`。タグの例は `cnako`、`wnako`、`cnako+wnako`。 |
| Native Source | `{scope}__{name}-{version}-native-source.npkg` |
| Native Prebuilt | `{scope}__{name}-{version}-native-{target_triple}-abi{abi_version}.npkg` |

### 3.2 Canonical ZIP

`pack` は正規形で標準 ZIP を生成する。レジストリは公開時、クライアントは展開時に次の条件をすべて検査し、違反があれば処理を中断して拒否する（MUST）。

1. 圧縮方式は DEFLATE または STORED。エントリパスは UTF-8 の相対パスで、`/` を区切りに使う。先頭の `/`、`.` と `..` のセグメント、ドライブ文字による指定、制御文字とバックスラッシュを禁止する。
2. UTF-8 のパスのバイト列を昇順に格納する。DOS タイムスタンプを `1980-01-01 00:00:00` に固定する。
3. シンボリックリンク、デバイスファイル、暗号化エントリ、不正な ZIP64 サイズヘッダを禁止する。完全一致または大文字小文字を無視した比較で名前が重複するエントリを拒否する。
4. 既定の上限は圧縮後 `25 MiB`、展開後合計 `100 MiB`、総ファイル数 `2,000`。上限は設定で変更してよい（MAY）。特例の外部参照には別途、圧縮後サイズ上限を適用する。実際に展開した量を逐次計上し、上限超過で直ちに中断する。圧縮率の数値による追加判定は [O06](open-questions.md#o06) を参照。
5. ルートの `NAKO-PKG/` に通常ファイル `METADATA.toml`、`FILES.json`、`COMMANDS.json` をすべて配置する。独立したディレクトリエントリの扱いは [O06](open-questions.md#o06) を参照。

### 3.3 `NAKO-PKG/METADATA.toml`

`schema_version = 1`。レジストリはアップロードされたアーカイブ内のこのファイルを解析し、アーティファクトのメタデータの正本として検証する（MUST）。 [サンプル](../fixtures/v1/requirements/METADATA.toml) / [スキーマ](../schemas/v1/npkg-metadata.schema.json)

- `package` に `id`、公開用 `version`、`license` と配布時の説明、リポジトリ、キーワード、capabilities を記録する。
- `artifact` に `kind` と空でない `runtimes` を記録する（MUST）。`native-prebuilt` は `artifact.native` の `target_triple`、`abi_version`、`library_path` が必須（MUST）。GNU Linux（`*-linux-gnu`）では `glibc_min` が必須で、他の組合せでは省略する（MUST）。`native-source` の ABI の記録位置は [O07](open-questions.md#o07) を参照。
- トップレベルの `engines`、`exports`、`features` は §2 の対応する構造を使う。`dependencies` は確定した依存の配列で、開発用依存を収録してはならない（MUST NOT）。
- 各依存に `id` と `req` を記録する。`features`、`default_features`、`optional`、`runtimes` で関連する条件を表す。`runtimes` を省略すると全ランタイム共通とする（MUST）。

### 3.4 `NAKO-PKG/FILES.json`

`schema_version: 1` と `files` 配列を持つ。`files` の各要素は `path`、バイト単位の `size`、`sha256` を持つ。`path` 昇順で、`FILES.json` 自身を除くすべての通常ファイルと 1 対 1 で対応しなければならない（MUST）。`METADATA.toml` と `COMMANDS.json` も対象になる。余分な項目、欠落、実バイト列との長さ・ハッシュ不一致を拒否する（MUST）。 [サンプル](../fixtures/v1/requirements/FILES.json) / [スキーマ](../schemas/v1/npkg-files.schema.json)

### 3.5 `NAKO-PKG/COMMANDS.json`

`schema_version: 1`、`exports_global_commands`、`exports` を持つ。`exports` は各サブパスを `binding`、`commands`、`constants` へ対応付ける。命令のデータは `name`、`kind`、`args` と、記述する場合は `return_type`、`async`、`doc` を持つ。引数のデータは `name`、助詞の配列 `josi` と、記述する場合は `type` を持つ。定数は名前の配列で表す。 [サンプル](../fixtures/v1/requirements/COMMANDS.json) / [スキーマ](../schemas/v1/npkg-commands.schema.json)

`exports` のキー集合と各 `binding` は、`METADATA.toml` の `exports`（省略された `binding` は `scoped`）と一致しなければならない（MUST）。`global` の入口が一つでもある場合に限り `exports_global_commands` を `true` にする（MUST）。§5.3 と §6.2 が用いる `global_commands` は `global` の入口が公開する命令名を指す。抽出・照合の詳細は [O08](open-questions.md#o08) を参照。

## 4. Sparse Index JSON

### 4.1 読み取りとキャッシュ

クライアントの依存解決に必要なレジストリ読み取りは、静的 HTTP GET だけで完結する（MUST）。

| エンドポイント | 応答 |
| --- | --- |
| `GET /index/v1/config.json` | レジストリ設定（§4.2）。 |
| `GET /index/v1/packages/{scope}/{name}.json` | パッケージ単位の版一覧（§4.3）。 |

パッケージインデックスは `ETag` と `Cache-Control` を返し、クライアントは再検証に `If-None-Match` を使う（MUST）。Cache-Control の例は `public, max-age=60, stale-while-revalidate=300`。不変のアーティファクト URL の配信には `Cache-Control: public, max-age=31536000, immutable` を使う（MUST）。

### 4.2 レジストリ設定と配信元

`schema_version: 1`、`registry_id`、`api_base_url`、`artifact_base_url`、`allowed_external_hosts` を返す。標準の配信先には `artifact_base_url` 配下を使う（SHOULD）。特例として、許可リストに含まれる HTTPS ホストを参照してよい（MAY）。 [サンプル](../fixtures/v1/requirements/config.json) / [スキーマ](../schemas/v1/sparse-index-config.schema.json)

中央配信は URL を解析して同一オリジンかつ基底パス配下であることを確認する。外部配信は解析したホストが `allowed_external_hosts` の要素と一致することを確認する。どちらも HTTPS と照合済み SHA-256 が必須（MUST）。リダイレクトを許可する場合は、取得前に各転送先にも同じ配信元制約を適用する（MUST）。許可するリダイレクトの範囲などは [O10](open-questions.md#o10) を参照。

### 4.3 パッケージインデックス

パッケージ単位で `schema_version: 1`、`id`、`scope_id`、`updated_at`、`deprecated`、`versions` を表す。`scope_id` の採番方式は [O03](open-questions.md#o03) を参照。 [サンプル](../fixtures/v1/requirements/package.json) / [スキーマ](../schemas/v1/sparse-index-package.schema.json)

版ごとに `version`、`published_at`、`yanked`、`yank_reason`、`license`、`capabilities`、`engines`、`exports_global_commands`、`global_commands`、`features`、`dependencies`、`provenance`、`artifacts`、`advisories` を表す。`provenance` は `verified` と、GitHub Actions の例では `provider`、`repository`、`repository_id`、`commit_sha`、`workflow_ref`、`run_id` で公開元を記録する。

各アーティファクトは `kind`、`runtimes`、`target`、`hosting`、`url`、`sha256`、`size` を持つ。`hosting` は中央配信の `registry` と特例の `external` を区別する。`target` は `universal` と `esm` では `null`、`native-source` では `abi_version`、`native-prebuilt` では `target_triple`、`abi_version` および GNU Linux の場合の `glibc_min` を持つ。

## 5. CI 集約とアトミック公開 API

CI の最終ジョブで複数 OS の成果物を集め、一つの論理バージョンを一回の要求で公開する。

### 5.1 公開要求と認証

`POST /v1/packages/{scope}/{name}/releases` は `multipart/form-data` を受け付ける。必須パートは `release` 一つ（`application/json`）と `artifact[]` 一つ以上（`application/octet-stream`、中央配信用 `.npkg`）。URL の Package ID、`release.id`、および各アーカイブ内の ID は一致しなければならない（MUST）。`release.version` は各アーカイブ内の版と一致しなければならない（MUST）。

CI は `POST /v1/auth/oidc/exchange` で GitHub OIDC JWT をレジストリ用の短命トークンへ交換し、`Authorization: Bearer {short_lived_registry_token}` を送る。レジストリは GitHub OIDC の JWKS で JWT を検証し、不変の `repository_id` を照合する（MUST）。手動公開に短命アクセストークンを使ってよい（MAY）。手動公開時は `provenance.verified = false` と記録する（MUST）。認証の詳細は [O11](open-questions.md#o11) を参照。

### 5.2 `release` パート

`schema_version: 1`、`id`、`version`、`uploaded_artifacts` を持つ。`uploaded_artifacts` の各項目は `filename` と `sha256` を持ち、アップロードするファイルに対応する。外部参照を使う場合は `external_artifacts` に `url` と `sha256` の組を記述する。サーバーは初期段階で外部参照を管理者フラグまたは許可リストで制限・閉鎖してよい（MAY）。 [サンプル](../fixtures/v1/requirements/release.json) / [スキーマ](../schemas/v1/publish-release.schema.json)

### 5.3 検証とコミット

以下の順序で処理する（MUST）。検証に一つでも失敗した場合は DB、ストレージ、インデックスを変更せずにエラーを返す（MUST）。

1. **権限と不変性。** 認証主体に `{scope}` または `{scope}/{name}` の公開権限があることを確認する。公開済みの `(id, version)` は yank 済みを含めて `409 Conflict` で拒否する。同じ内容による再公開にも適用する。
2. **クォータ。** 1 ファイル、1 リリースの合計、スコープ総容量の三つの上限を検査する。具体値は [O16](open-questions.md#o16) を参照。
3. **ハッシュ。** 各 `artifact[]` の実バイト列の SHA-256 を計算し、対応する `uploaded_artifacts` の申告値と照合する。
4. **個別検証。** 全 `.npkg` を §3.2 に従ってメモリまたは一時ディレクトリへ安全に展開し、§3.3〜§3.5 を検証する。
5. **クロス検証。** 全 `.npkg` の `METADATA.toml` にある `package.id`、`package.version`、`package.license`、`package.capabilities`、`engines`、`exports`、`features`、`dependencies` と、`COMMANDS.json` から得る `exports_global_commands`、`global_commands` の値が一致しなければならない。同じ `(kind, runtimes, target_triple, abi_version)` のアーティファクトが二つ以上あれば拒否する。比較時の正規化は [O08](open-questions.md#o08) を参照。
6. **依存の存在。** `dependencies` の全 ID が存在し、それぞれの `req` を満たす非 yank 版が最低一つ存在することを確認する。
7. **確定の順序。** 全 `.npkg` を S3/R2 の不変パスへ格納する。キーはバージョンとハッシュを含む。その後 PostgreSQL トランザクションでリリース、アーティファクト、provenance を INSERT する。最新版を含めたパッケージ Sparse Index を生成し、オブジェクトを原子的に置き換えて CDN キャッシュをパージする。インデックス反映の失敗時は非同期リトライジョブで収束させる（MUST）。

同版の並行公開でも公開済みの版を置き換えてはならない（MUST NOT）。要件は保存順序とインデックス反映の再試行を定めている。DB やストレージへの書き込み開始後の障害については、無変更で失敗する条件との整合、API の応答と公開確定点を [O09](open-questions.md#o09) で扱う。外部参照を有効にする場合の検証と保存の境界は [O10](open-questions.md#o10) を参照。

## 6. クライアントのリゾルバとインポート

### 6.1 省略名と命令スコープ

- プロジェクトのローカル解決表は `dependencies` と現在のプロファイルに対応する `runtime-dependencies` の直接依存だけで構築する（MUST）。間接依存をコードから直接インポートしてはならない（MUST NOT）。
- ローカル名は明示した `alias`、省略した場合は ID の `name` 部分とする（MUST）。一つの省略名に複数の直接依存が対応し、その名前をコードが使った場合はコンパイルエラー（Ambiguous Import）とする（MUST）。利用者は別名を指定するか、直接依存の完全修飾 ID で指定できる。
- `scoped` の命令はモジュール名前空間または指定した別名の内部に登録する（MUST）。グローバル命令空間に登録してはならない（MUST NOT）。`global` の入口を取り込む場合にグローバル命令空間へ登録する。`allow_global_commands = true` が明示されていない依存から `global` を取り込もうとした場合は、既定でエラーまたは厳格警告を出す（MUST）。 [O12](open-questions.md#o12)

### 6.2 ダイヤモンド依存と yank

- `exports_global_commands = false` のパッケージは同一プロファイル内で複数メジャー版を共存させてよい（MAY）。
- `exports_global_commands = true` のパッケージは同一プロファイル内で厳密に単一バージョンに収束させる（MUST）。収束不能または異なるパッケージの `global_commands` 間に命令名衝突があれば、依存解決をエラーにする（MUST）。
- `yanked = true` の版を新規解決で選んではならない（MUST NOT）。既存の `nako.lock` に記録があり、ハッシュが一致する場合は使用してよい（MAY）。その場合は警告を出す（MUST）。

### 6.3 アーティファクト選択

選択済みの版について、クライアントは次の優先順位で `artifacts` を走査し、最初に適合するものを採用する（MUST）。

| runtime | 優先順位 |
| --- | --- |
| `lnako` | ① `native-prebuilt`。triple が一致し、ABI が対応範囲内で、GNU Linux ならホストの glibc が `glibc_min` 以上。② ABI が対応範囲内の `native-source`。ローカルでビルドする。③ `universal`。 |
| `cnako` | ① `runtimes` に `cnako` を含む `esm`。② `universal`。 |
| `wnako` | ① `runtimes` に `wnako` を含む `esm`。② `universal`。 |

どの候補にも適合しなければ非対応エラーとする（MUST）。`lnako` の診断には利用可能な `runtimes` と `target_triple` を列挙する（MUST）。

### 6.4 ダウンロードと `nako.lock`

取得先に §4.2 の HTTPS と配信元検査を適用する（MUST）。ダウンロード直後に `.npkg` 実バイト列の SHA-256 を計算し、インデックスの `sha256` と lock に記録した `sha256` の双方と一致することを確認してから展開する（MUST）。一方でも不一致なら展開してはならない（MUST NOT）。lock の新しい構造と移行は [O02](open-questions.md#o02)、[O13](open-questions.md#o13) を参照。

## 7. 共通スキーマと適合性試験

[七つの JSON Schema](../schemas/v1/) を Draft 2020-12 で提供する。TOML 用の二つは TOML をパースして JSON と同じオブジェクト、配列、スカラーへ写像したデータに適用する。TOML の構文と整数型の検査は変換前に行う。JSON Schema の `default` は注釈であり、`binding` の実際の補完は利用側で行う。相対 `$ref` は同じディレクトリ内のファイルを参照する。 [Draft 2020-12 検証仕様](https://json-schema.org/draft/2020-12/json-schema-validation)

スキーマは単体の構造を検査する。SPDX 式、範囲式、feature の循環、ZIP と実バイト列、複数ファイル間の一致、権限、依存グラフ、配信元の検証には本文の規則を適用する。ドラフトで必須性や形を仮置きした欄の一覧は [O14](open-questions.md#o14) を参照。

共有ライブラリ `nako-pkg-core` に識別子、Canonical ZIP、アーティファクト間整合性、ターゲット選択と省略インポート表を集約する構成を推奨する（SHOULD）。レジストリは Rust、Axum、PostgreSQL、S3/R2 で OIDC 交換、公開、yank、静的インデックス生成を分割できる。yank の推奨経路は `POST /v1/packages/{scope}/{name}/{version}/yank` で、撤回後にインデックスを再生成する。認証と要求・応答の詳細は [O15](open-questions.md#o15) を参照。

`lnako` とレジストリは [適合性フィクスチャ一覧](../fixtures/v1/conformance.md) の同じ入力と期待結果を使う。着手順序は [実装準備メモ](implementation-plan.md)、実行済みの確認は [スキーマ検証記録](schema-validation.md) を参照。
