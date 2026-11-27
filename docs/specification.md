# なでしこパッケージ形式・レジストリ仕様 v1

適用範囲は `lnako`、`cnako`、`wnako`、`nako-registry`。本文の節番号は「パッケージ形式・レジストリ仕様 要件（2026-11-27 みかん提示）」の §1〜§7 に対応する。初版の運用と要件の補足はオーナーとの Q1〜Q38 の合意に従う。合意の対応関係と残作業は [判断記録](open-questions.md) を参照。

初版は匿名取得できる公開パッケージを対象とする。非公開配布は別途設計する。旧パッケージ ID、manifest、`.npkg`、index、静的 PUT、旧 lock の互換経路は設けない。旧形式を検出できる場合、診断には新形式が必要なことと、再作成が必要な入力を示す（MUST）。暗黙の変換は行わない（MUST NOT）。 [非公開パッケージの後続設計](https://github.com/soramikan/nako-registry/issues/6)

`MUST` と `MUST NOT` は必須と禁止、`SHOULD` は推奨、`MAY` は任意を表す。 [RFC 2119](https://www.rfc-editor.org/info/rfc2119/)

## 1. 共通規約・識別子・基本型

### 1.1 パッケージ識別子

レジストリ上の Package ID は `@{scope}/{name}` を使う（MUST）。`scope` は `^[a-z][a-z0-9-]{1,38}$`、`name` は `^[a-z][a-z0-9-]{0,63}$` にそれぞれ文字列全体が一致しなければならない（MUST）。どちらも末尾の `-` と連続する `--` を拒否する（MUST）。大文字を含む入力は拒否し、検証済みの小文字表現で比較、保存、URL 生成を行う（MUST）。

一般利用者による `std`、`nako`、`nadesiko`、`nadesiko3`、`lnako`、`cnako`、`wnako`、`core`、`official`、`registry`、`system`、`internal` の登録を拒否する（MUST）。予約判定は一般登録の権限検査で行う。たとえば `@std/json` は依存の ID として構文上有効であり、参照先の存在は別途確認する。

初版では管理者が所有者と公開元を確認して scope を払い出す。サーバーは一意の `scope_id` を割り当て、クライアントは不透明な ID として扱う（MUST）。公開実績のある scope 名は固定する（MUST）。所有権移転は管理者だけが実行できる（MUST）。移転時も scope 名、Package ID、`scope_id` を保持し、移転前の所有権に基づく公開許可を失効させる。移転前後の所有者と権限変更を監査記録に残す（MUST）。

### 1.2 バージョン・ハッシュ・日時・ターゲット

| 値 | 要件 |
| --- | --- |
| バージョン | SemVer 2.0.0 に厳格に従う（MUST）。公開バージョン文字列にビルドメタデータ `+...` を含めてはならない（MUST NOT）。 |
| ハッシュ | `sha256:` に小文字16進数64桁を続ける（MUST）。 |
| 日時 | UTC の RFC 3339 を使う（MUST）。例は `2026-11-27T13:30:00Z`。 |
| `runtime` | `lnako`、`cnako`、`wnako` のいずれか（MUST）。 |
| `target_triple` | LLVM/Zig 準拠の `{arch}-{os}-{abi}`（MUST）。例は `aarch64-macos-none`、`x86_64-linux-gnu`、`x86_64-linux-musl`、`x86_64-windows-msvc`。 |
| `capabilities` | `pure-nako`、`native`、`ffi`、`fs`、`net`、`env`、`process`、`unsafe` から宣言する（MUST）。純粋ななでしこの宣言例は `["pure-nako"]`。 |

依存と engine の SemVer Range は `node-semver` 7.7.4 の既定の範囲構文と適合判定に従う（MUST）。`loose` と `includePrerelease` は無効とする。各処理系は同じ境界値を共通フィクスチャで検証する。 [node-semver 7.7.4](https://github.com/npm/node-semver/tree/v7.7.4#ranges) / [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html) / [RFC 3339](https://www.rfc-editor.org/info/rfc3339/)

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
| `package` | 配布用 `.npkg` の生成時と公開時は `id`、公開用 `version`、`license`（SPDX 式）が必須（MUST）。ローカル専用プロジェクトではこの三項目を省略できる（MAY）。説明、配布元リポジトリ、ホームページ、README のパス、キーワード、capabilities を記述できる。 |
| `package.engines` | ランタイム名から対応する SemVer Range への表。 |
| `exports` | `.` が既定の入口、`./client` のようなキーが公開サブパス。各値は `entry` と任意の `binding` を持つ。 |
| `features` | feature 名から追加で有効にする feature の配列への表。`default` に既定の feature 群を記述できる。 |
| `artifacts.universal` | `include` に収録対象を記述する。 |
| `artifacts.esm` | `runtimes`、`entry`、`include` に ESM の配布対象を記述する。 |
| `artifacts.native` | `abi_version`、`source_include`、`prebuilt_lib_name` にソースとビルド済みライブラリの組み立て情報を記述する。 |
| `dependencies`、`runtime-dependencies.<runtime>`、`dev-dependencies` | キーは完全修飾 Package ID。値はバージョン範囲の文字列か、`version` と任意の `alias`、`features`、`allow_global_commands` を持つ表。 |
| `profiles.<profile>` | `runtime` に解決対象のランタイムを記述する。`default` はプロファイル名の例。 |

未知のトップレベルキーを拒否する（MUST）。TOML の `schema_version = 1.0` は整数 `1` と区別する（MUST）。`binding` の省略は `scoped` と扱い、`global` が一つでもあれば `exports_global_commands = true` と判定する（MUST）。ローカル解決名の重複はビルドまたは解決時に検査する（MUST、§6.1）。feature は加算的で、循環参照を拒否する（MUST）。 [SPDX 式](https://spdx.github.io/spdx-spec/v2.3.1/SPDX-license-expressions/)

公開時は `license` の SPDX 式を検証する（MUST）。`LicenseRef-…` を使用する場合は、参照と本文の対応が分かる形で、該当するライセンス本文を各 `.npkg` に収録する（MUST）。

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

`pack` は正規形で標準 ZIP を生成する。同じ入力、同じ `pack` の版、同じ設定から生成した `.npkg` はバイト単位で一致する（MUST）。他の生成器が作った `.npkg` の受理条件は正規形への適合とする。レジストリは公開時、クライアントは展開時に次の条件をすべて検査し、違反があれば処理を中断して拒否する（MUST）。

1. 圧縮方式は DEFLATE または STORED。エントリパスは UTF-8 の相対パスで、`/` を区切りに使う。先頭の `/`、`.` と `..` のセグメント、ドライブ文字による指定、制御文字とバックスラッシュを禁止する。
2. UTF-8 のパスのバイト列を昇順に格納する。DOS タイムスタンプを `1980-01-01 00:00:00` に固定する。
3. シンボリックリンク、デバイスファイル、暗号化エントリ、不正な ZIP64 サイズヘッダを禁止する。完全一致または大文字小文字を無視した比較で名前が重複するエントリを拒否する。
4. 既定の上限は圧縮後 `25 MiB`、展開後合計 `100 MiB`、総ファイル数 `2,000`。上限は設定で変更してよい（MAY）。特例の外部参照には別途、圧縮後サイズ上限を適用する。実際に展開した量を逐次計上し、上限超過で直ちに中断する。圧縮率の数値による追加判定は [O06](open-questions.md#o06) を参照。
5. ルートの `NAKO-PKG/` に通常ファイル `METADATA.toml`、`FILES.json`、`COMMANDS.json` をすべて配置する。ディレクトリは通常ファイルのパスで表現し、`NAKO-PKG/` 自体を含む独立したディレクトリエントリを禁止する。

### 3.3 `NAKO-PKG/METADATA.toml`

`schema_version = 1`。レジストリはアップロードされたアーカイブ内のこのファイルを解析し、アーティファクトのメタデータの正本として検証する（MUST）。 [サンプル](../fixtures/v1/requirements/METADATA.toml) / [スキーマ](../schemas/v1/npkg-metadata.schema.json)

- `package` に `id`、公開用 `version`、`license` と配布時の説明、リポジトリ、キーワード、capabilities を記録する。
- `artifact` に `kind` と空でない `runtimes` を記録する（MUST）。`native-prebuilt` は `artifact.native` の `target_triple`、`abi_version`、`library_path` が必須（MUST）。GNU Linux（`*-linux-gnu`）では `glibc_min` が必須で、他の組合せでは省略する（MUST）。`native-source` は `artifact.native.abi_version` が必須（MUST）。ソース用の `target_triple` と `library_path` は不要。レジストリはこの ABI を index の `target.abi_version` に写す（MUST）。
- トップレベルの `engines`、`exports`、`features` は §2 の対応する構造を使う。これらと `dependencies` はリリース共通で、アーティファクトの対応ランタイムに合わせて項目を削ってはならない（MUST NOT）。`dependencies` は確定した依存の配列で、開発用依存を収録してはならない（MUST NOT）。
- 各依存に `id` と `req` を記録する。`features`、`default_features`、`optional`、`runtimes` で関連する条件を表す。依存に `alias` または `allow_global_commands` を指定した場合はその値を保持する（MUST、§6.1）。`allow_global_commands` を省略した場合は `false` とする。`runtimes` を省略すると全ランタイム共通とする（MUST）。

リリース共通の `exports` は公開サブパス、`binding`、共通の `entry` を定める。種別固有の収録先は任意の `[artifact.entries]` にサブパスからアーカイブ内相対パスへの対応として記録する。記録がないサブパスには共通の `entry` を使う。対応表のキーは共通 `exports` に含まれ、選択されるパスはそのアーカイブ内の通常ファイルを指さなければならない（MUST）。たとえば ESM は `"." = "dist/esm/index.js"` を記録して共通の `.nako3` ファイルの同梱を省ける。`native-source` でローカルビルドが必要な場合、対応表はアーカイブ内のビルド入力を指し、実行時の生成物を同梱する必要はない。

### 3.4 `NAKO-PKG/FILES.json`

`schema_version: 1` と `files` 配列を持つ。`files` の各要素は `path`、バイト単位の `size`、`sha256` を持つ。`path` 昇順で、`FILES.json` 自身を除くすべての通常ファイルと 1 対 1 で対応しなければならない（MUST）。`METADATA.toml` と `COMMANDS.json` も対象になる。余分な項目、欠落、実バイト列との長さ・ハッシュ不一致を拒否する（MUST）。 [サンプル](../fixtures/v1/requirements/FILES.json) / [スキーマ](../schemas/v1/npkg-files.schema.json)

### 3.5 `NAKO-PKG/COMMANDS.json`

`schema_version: 1`、`exports_global_commands`、`exports` を持つ。`exports` は各サブパスを `binding`、`commands`、`constants` へ対応付ける。命令のデータは `name`、`kind`、`args` と、記述する場合は `return_type`、`async`、`doc` を持つ。引数のデータは `name`、助詞の配列 `josi` と、記述する場合は `type` を持つ。定数は名前の配列で表す。 [サンプル](../fixtures/v1/requirements/COMMANDS.json) / [スキーマ](../schemas/v1/npkg-commands.schema.json)

`exports` のキー集合と各 `binding` は、`METADATA.toml` の `exports`（省略された `binding` は `scoped`）と一致しなければならない（MUST）。`global` の入口が一つでもある場合に限り `exports_global_commands` を `true` にする（MUST）。§5.3 と §6.2 が用いる `global_commands` は `global` の入口の `commands[].name` から作る集合とする（MUST）。定数名はこの集合に含めない（MUST NOT）。

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

パッケージ単位で `schema_version: 1`、`id`、`scope_id`、`updated_at`、`deprecated`、`versions` を表す。`scope_id` は §1.1 の不透明な ID とする。 [サンプル](../fixtures/v1/requirements/package.json) / [スキーマ](../schemas/v1/sparse-index-package.schema.json)

版ごとに `version`、`published_at`、`yanked`、`yank_reason`、`license`、`capabilities`、`engines`、`exports_global_commands`、`global_commands`、`features`、`dependencies`、`provenance`、`artifacts`、`advisories` を表す。`provenance` は `verified` と、GitHub Actions の例では `provider`、`repository`、`repository_id`、`commit_sha`、`workflow_ref`、`run_id` で公開元を記録する。

各アーティファクトは `kind`、`runtimes`、`target`、`hosting`、`url`、`sha256`、`size` を持つ。`hosting` は中央配信の `registry` と特例の `external` を区別する。`target` は `universal` と `esm` では `null`、`native-source` では `abi_version`、`native-prebuilt` では `target_triple`、`abi_version` および GNU Linux の場合の `glibc_min` を持つ。

## 5. CI 集約とアトミック公開 API

CI の最終ジョブで複数 OS の成果物を集め、一つの論理バージョンを一回の要求で公開する。

### 5.1 公開要求と認証

`POST /v1/packages/{scope}/{name}/releases` は `multipart/form-data` を受け付ける。必須パートは `release` 一つ（`application/json`）と `artifact[]` 一つ以上（`application/octet-stream`、中央配信用 `.npkg`）。URL の Package ID、`release.id`、および各アーカイブ内の ID は一致しなければならない（MUST）。`release.version` は各アーカイブ内の版と一致しなければならない（MUST）。

CI は `POST /v1/auth/oidc/exchange` で GitHub OIDC JWT をレジストリ用の短命トークンへ交換し、`Authorization: Bearer {short_lived_registry_token}` を送る。初版の公開認証はこの経路に限る（MUST）。レジストリは GitHub OIDC の JWKS で JWT を検証し、不変の `repository_id` と公開用 workflow を対象パッケージの登録情報と照合する（MUST）。実行元は `refs/tags/v{version}` に一致する保護済みの公開タグでなければならない（MUST）。タグの保護はタグ名との一致とは別に確認する。交換したトークンが認める対象 ID と版は公開 POST でも照合する（MUST）。手動公開用トークン発行は後続とし、導入する場合は手動公開を `provenance.verified = false` と記録する（MUST）。 [GitHub Actions の OIDC クレーム](https://docs.github.com/en/actions/reference/security/oidc)

### 5.2 `release` パート

`schema_version: 1`、`id`、`version`、`uploaded_artifacts` を持つ。`uploaded_artifacts` の各項目は `filename` と `sha256` を持ち、アップロードするファイルに対応する。`external_artifacts` は外部参照を有効にする場合の `url` と `sha256` の組を表す。初版では中央へのアップロードだけを受け付け、`external_artifacts` は空または省略とする。値が一つでもあれば公開を拒否する（MUST）。 [サンプル](../fixtures/v1/requirements/release.json) / [スキーマ](../schemas/v1/publish-release.schema.json)

### 5.3 検証とコミット

以下の順序で処理する（MUST）。検証に一つでも失敗した場合は DB、ストレージ、インデックスを変更せずにエラーを返す（MUST）。

1. **権限と不変性。** 認証主体に対象パッケージの有効な公開権限があることを確認する。所有権移転などで失効済みの権限は、トークンの有効期間内でも認めない。公開済みの `(id, version)` は yank 済みを含めて `409 Conflict` で拒否する。同じ内容による再公開にも適用する。
2. **クォータ。** ZIP の安全上限とは別に、1 ファイル、1 リリースの合計、スコープ総容量の三つの上限を検査する。yank 済みでも配布物を保管している間はスコープ総容量に計上する（MUST）。具体値は配布物の実測とストレージ予算から決める。 [残作業 O16](open-questions.md#o16)
3. **ハッシュ。** 各 `artifact[]` の実バイト列の SHA-256 を計算し、対応する `uploaded_artifacts` の申告値と照合する。
4. **個別検証。** 全 `.npkg` を §3.2 に従ってメモリまたは一時ディレクトリへ安全に展開し、§3.3〜§3.5 を検証する。
5. **クロス検証。** 全 `.npkg` の `METADATA.toml` にある `package.id`、`package.version`、`package.license`、`package.capabilities`、`engines`、`exports`、`features`、`dependencies` と、`COMMANDS.json` から得る `exports_global_commands`、`global_commands` が一致しなければならない。仕様上の既定値を補った上で比較し、表のキー順と集合の要素順は無視する。順序に意味がある値を照合する場合は順序も比較する。`artifact.entries` はアーティファクト固有。`runtimes` を集合として比較し、同じ `(kind, runtimes, target_triple, abi_version)` のアーティファクトが二つ以上あれば拒否する。
6. **依存の存在。** `dependencies` の全 ID が存在し、それぞれの `req` を満たす非 yank 版が最低一つ存在することを確認する。
7. **確定の順序。** 全 `.npkg` を S3/R2 の不変パスへ格納する。キーはバージョンとハッシュを含む。その後 PostgreSQL トランザクションでリリース、アーティファクト、provenance を INSERT する。最新版を含めたパッケージ Sparse Index を生成し、オブジェクトを原子的に置き換えて CDN キャッシュをパージする。インデックス反映の失敗時は非同期リトライジョブで収束させる（MUST）。

書き込み開始後かつ DB 確定前の障害では、利用者に見える版と配信状態を維持する（MUST）。非公開の一時オブジェクトが残る場合は再試行または回収の対象とする（MUST）。DB 確定を公開要求の確定点とし、その後は索引反映待ちの状態を返してよい（MAY）。同じ `(id, version)` への再送は、反映待ち、配信開始済み、yank 済みのいずれでも `409 Conflict` とする。同版の並行要求も確定済みの内容を置き換えてはならない（MUST NOT）。

### 5.4 公開状態の照会

初版は認証付きの照会を提供し、対象版の DB 確定後に「索引反映待ち」と「配信開始済み」を区別する（MUST）。配信開始済みは、公開の Sparse Index に版が反映され、利用者が対応するアーティファクトを取得できる状態を指す。公開 CLI と公式 CI は配信開始を確認してから完了を報告する。待機上限までに確認できなければ「反映待ち」と報告し、同版の公開要求を自動再送しない（MUST NOT）。一般の利用者は §4 の配信経路で取得する。

## 6. クライアントのリゾルバとインポート

### 6.1 省略名と命令スコープ

- プロジェクトのローカル解決表は `dependencies` と現在のプロファイルに対応する `runtime-dependencies` の直接依存だけで構築する（MUST）。間接依存をコードから直接インポートしてはならない（MUST NOT）。
- ローカル名は明示した `alias`、省略した場合は ID の `name` 部分とする（MUST）。一つの省略名に複数の直接依存が対応し、その名前をコードが使った場合はコンパイルエラー（Ambiguous Import）とする（MUST）。利用者は別名を指定するか、直接依存の完全修飾 ID で指定できる。
- `scoped` の命令はモジュール名前空間または指定した別名の内部に登録する（MUST）。グローバル命令空間に登録してはならない（MUST NOT）。依存の `alias` と `allow_global_commands` はその依存を宣言したパッケージのスコープに適用する。別の依存へ継承してはならない（MUST NOT）。
- `global` の入口の取り込みには、宣言元の依存に `allow_global_commands = true` が必要（MUST）。ルート以外のパッケージからの取り込みであっても、ルートが同じ提供元を直接依存に宣言し、その依存に `allow_global_commands = true` を明示しなければならない（MUST）。いずれかの許可がなければコンパイルエラーとし、グローバル命令を登録しない（MUST）。

### 6.2 ダイヤモンド依存と yank

- 同一プロファイルのある Package ID で選択する版がすべて `exports_global_commands = false` なら、共通の一版を優先する（SHOULD）。要求範囲が交わらない場合は同一メジャー内を含め複数版を共存させてよい（MAY）。
- `exports_global_commands = true` の版を採用するなら、同じ Package ID は同一プロファイル内で単一バージョンに収束させる（MUST）。同じ ID の scoped 版も併用できない。収束不能または異なるパッケージの `global_commands` 間に命令名衝突があれば、依存解決をエラーにする（MUST）。
- `yanked = true` の版を新規解決で選んではならない（MUST NOT）。既存の `nako.lock` に記録があり、ハッシュが一致する場合は使用してよい（MAY）。その場合は警告を出す（MUST）。

### 6.3 アーティファクト選択

選択済みの版について、クライアントは次の優先順位で `artifacts` を走査し、最初に適合するものを採用する（MUST）。

| runtime | 優先順位 |
| --- | --- |
| `lnako` | ① `native-prebuilt`。triple が一致し、ABI が対応範囲内で、GNU Linux ならホストの glibc が `glibc_min` 以上。② ABI が対応範囲内で、プロジェクトが許可した `native-source` をローカルでビルド。③ `universal`。 |
| `cnako` | ① `runtimes` に `cnako` を含む `esm`。② `universal`。 |
| `wnako` | ① `runtimes` に `wnako` を含む `esm`。② `universal`。 |

どの候補にも適合しなければ非対応エラーとする（MUST）。`lnako` の診断には利用可能な `runtimes` と `target_triple` を列挙する（MUST）。

`native-source` の実行許可は、ルートプロジェクトが対象 Package ID と解決ノードで固定するアーティファクトの SHA-256 に対して明示する（MUST）。候補の評価時は index のハッシュで照合し、実行前に §6.4 の実バイト列および lock の照合を完了する（MUST）。同じ ID でもハッシュが変われば再許可が必要。未許可の候補は飛ばして `universal` を探し、ほかの適合候補がなければ許可が必要だと診断する（MUST）。CI でも同じ規則を適用する。

### 6.4 ダウンロードと `nako.lock`

`nako.lock` はプロファイルごとに解決済みの依存グラフを記録し、各ノードの Package ID、バージョン、選択したアーティファクトの SHA-256 を固定する（MUST）。同じ Package ID の複数版を区別する。index と lock のハッシュが同じで、§4.2 の配信元検査を通る場合は、URL が変わった配布物を取得してよい（MAY）。

取得先に §4.2 の HTTPS と配信元検査を適用する（MUST）。ダウンロード直後に `.npkg` 実バイト列の SHA-256 を計算し、インデックスの `sha256` と lock に記録した `sha256` の双方と一致することを確認してから展開する（MUST）。一方でも不一致なら展開してはならない（MUST NOT）。

## 7. 共通スキーマと適合性試験

[七つの JSON Schema](../schemas/v1/) を Draft 2020-12 で提供する。TOML 用の二つは TOML をパースして JSON と同じオブジェクト、配列、スカラーへ写像したデータに適用する。TOML の構文と整数型の検査は変換前に行う。JSON Schema の `default` は注釈であり、`binding` の実際の補完は利用側で行う。相対 `$ref` は同じディレクトリ内のファイルを参照する。 [Draft 2020-12 検証仕様](https://json-schema.org/draft/2020-12/json-schema-validation)

スキーマは単体の構造を検査する。pack・公開時の追加必須項目、SPDX 式と本文の同梱、範囲式、feature の循環、ZIP と実バイト列、複数ファイル間の一致、権限、依存グラフ、配信元の検証には本文の規則を適用する。この文書のフィールド定義を v1 初版の契約とし、公開後は既存フィールドの意味を固定する。既存実装が無視しても結果が変わらない任意項目は、拡張を許す場所に限り同じ版に追加できる（MAY）。依存解決または公開の受理条件に影響する追加には版の更新が必要（MUST）。§2 のトップレベルの拒否規則が優先する。

共有ライブラリ `nako-pkg-core` に識別子、Canonical ZIP、アーティファクト間整合性、ターゲット選択と省略インポート表を集約する構成を推奨する（SHOULD）。レジストリは Rust、Axum、PostgreSQL、S3/R2 で OIDC 交換、公開、yank、静的インデックス生成を分割できる。yank の経路は `POST /v1/packages/{scope}/{name}/{version}/yank` とする。対象パッケージの管理権限を持つ人またはレジストリ管理者だけが実行でき、理由は必須とする（MUST）。公開用 CI のトークンでは実行できない（MUST NOT）。理由を索引の `yank_reason` に反映し、操作主体と日時を監査記録に残す（MUST）。初版では yank を解除できない。必要に応じて新しいバージョンを公開する。

共通仕様・スキーマ・フィクスチャの正本は `nako-registry` に置く。各処理系は参照する版を固定し、レジストリと同じ [適合性フィクスチャ](../fixtures/v1/conformance.md) を使う（MUST）。着手順序は [実装準備メモ](implementation-plan.md)、実行済みの確認は [スキーマ検証記録](schema-validation.md) を参照。
