# 現行のパッケージ仕様・実装の調査

調査対象は `~/lnako-57-work/lnako` の `032020f0c620ec83f5ddaac986e963eca273605b` と `nako-registry` の作業開始時点 `c0aaaf0`。lnako の仕様とコードは `git show` と `git grep` で読み取った。レジストリ側の追跡ファイルは README のみだった。ここで示す実装状態はソースからの確認結果。CLI の実行や HTTP PUT は行っていない。

## 新要件の領域別調査

| 領域 | 現行文書の契約 | 固定版の実装 | 新要件 |
| --- | --- | --- | --- |
| 識別子 | Public ID は不変の `pkg:<32hex>`、Human ID は `@owner/name`。manifest の `package.id` は登録前なら省略できる。 | `registry.zig` は二つを別の型として検証し、索引を Public ID で突合する。`project_identity.zig` には取得元から仮の ID を得る経路がある。 | §1 は `@scope/name` をレジストリの Package ID とする。予約スコープは一般登録を禁止する。 |
| `nako.toml` | `[package]` に `name/version/license` が必須。`package.schema-version` は省略時 1。依存は取得元別（`pkg/npm/path/git/http`）、`[[exports]]` に `name/path/alias` と条件付き `native/esm`、プロファイルに `os/cpu/abi/compat-js` などを記述する。 | `manifest.zig` の TOML 解析と `manifest_validate.zig` の意味検証がこの構造を読み込む。feature の循環やエクスポートの重複を検査する。 | §2 は整数のトップレベル `schema_version`、公開時の完全修飾 ID、サブパスをキーとする `exports`、ランタイム別の配布情報と依存を定義する。 |
| `.npkg` | 一つの ZIP に複数実装を収録できる。STORED のみ。mtime はヘッダ上のゼロ値。 `METADATA.toml`、payload だけを対象とする `FILES.toml`、フラットな `commands.json` が必須。版キーは `schemaVersion`。 | `npkg_build.zig` が三つの制御ファイルと STORED ZIP を生成。`npkg_verify.zig` がヘッダ、連続配置、パス、重複、CRC、ファイル索引を検査する。最大エントリ数は 100,000、最大展開サイズは 1 GiB。 | §3 は種別・ターゲットごとの `.npkg`、固定 DOS 日時、DEFLATE の許容、制御ファイルを含む `FILES.json`、サブパス別 `COMMANDS.json` を定義する。 |
| index | `index.json`、`<owner>/<name>.json`、`<owner>/<name>/<version>.json` を分ける。中央版も静的版と同じ応答スキーマを使う計画。 | `registry.zig` の `StaticRegistry` が索引、パッケージ、版レコードを取得し、Public ID と版を照合する。 | §4 は `/index/v1/config.json` とパッケージ別の Sparse Index の GET に集約する。 |
| 公開 API | `PUBLISHING.md` §1 は publish を未実装とする。§4 は既定 dry-run、`--no-dry-run` で artifact → version → index の順に静的 PUT、同じ内容なら再処理成功と記述する。 | CLI は `package publish` を配線済み。`publish.zig` は manifest/lock と ZIP を検査し、版の既存状態を GET で確認してから、Bearer トークンで三段階 PUT する。版とハッシュが同一なら再送を省ける。中央 API のサーバーはこのレジストリには存在しない。 | §5 は CI 集約、短命トークン、multipart POST による一括公開、DB とオブジェクトの確定、公開済み版への `409` を定める。 |
| リゾルバ | 同一 Public ID はグラフで一度だけ解決。 `pkg:<alias>[/subpath]` は環境の依存スコープで引く。source 優先で、条件によって native/ESM を選ぶ。 | `resolver.zig` は共通バージョン制約を PubGrub で解決し、対応ランタイムを lnako/cnako とする。`chooseImplementation` は既定で source 優先。`import_resolver.zig` が環境と依存 alias を照合する。`registry.zig` は yank 版を候補から除外する。 | §6 は直接依存による解決表、グローバル命令の有無で変わるバージョン制約、三ランタイムの選択優先順位、インデックスと lock の両方によるハッシュ検証を定める。 |

固定版の仕様は [SPECIFICATION.md](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/docs/package-system/SPECIFICATION.md)、[PUBLISHING.md](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/docs/package-system/PUBLISHING.md)、[SCHEMA_VERSIONS.md](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/docs/package-system/SCHEMA_VERSIONS.md)。

主な確認箇所は [ID の検証](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/src/package/registry.zig#L461)、[manifest の解析](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/src/package/manifest.zig#L616)、[ZIP 検証](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/src/package/npkg_verify.zig#L267)、[索引の取得](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/src/package/registry.zig#L17)、[公開 CLI の分岐](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/src/cli/commands/package.zig#L357)、[公開の PUT 処理](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/src/package/publish.zig#L625)、[対象実装の選択](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/src/package/resolver.zig#L566)、[インポート解決](https://github.com/soramikan/lnako/blob/032020f0c620ec83f5ddaac986e963eca273605b/src/package/import_resolver.zig)。

## nako-registry Issue #1〜#6 と新要件

2026-11-27 UTC に `gh issue list --repo soramikan/nako-registry --state all` で本文を確認した。6件とも OPEN。

| Issue | 現行計画 | 今回の対応と残る論点 |
| --- | --- | --- |
| #1 静的レジストリ・所有者登録・共通取得 API | Pages 配信と作者 Releases、旧 v1/v2 の取得形式、初回所有者確認。 | 静的取得は §4、登録権限は §1.1・§5.3。旧形式の互換は設けず、scope の払い出しは管理者が担当する（O02/O03）。 [#1](https://github.com/soramikan/nako-registry/issues/1) |
| #2 信頼済み公開 CI と静的インデックス自動登録 | Releases を定期取込し、workflow と attestation を確認。同一内容を冪等に再処理。 | §5.1〜§5.3 の CI 最終ジョブによる POST・OIDC・全件検証へ変更。Releases の定期取込は引き継がず、初版は登録済み workflow と保護済みタグを照合する（O02/O11）。 [#2](https://github.com/soramikan/nako-registry/issues/2) |
| #3 中央 API・PostgreSQL・S3 互換保存 | 匿名取得、全件検証後に公開、Rust・Axum・PostgreSQL・S3 互換。 | §3〜§5、§7。全件検証と保存構成を引き継ぎ、取得形式と再公開の扱いを更新する。DB 確定後の索引反映はレジストリ側で再試行する（O09）。 [#3](https://github.com/soramikan/nako-registry/issues/3) |
| #4 所有者認証・CI 公開・所有権移転・yank | 登録元の確認、管理権限、移転、yank、監査。 | §1.1・§5.1・§5.3・§6.2・§7。scope 移転は管理者が担当し、yank は権限のある人に限定する（O03/O11/O15）。 [#4](https://github.com/soramikan/nako-registry/issues/4) |
| #5 移行・旧 lock・復旧・監視 | 静的データと旧 lock の維持。同じ hash での取得、切替とロールバック。 | §4・§6.4 は新形式の取得とハッシュ照合を規定する。旧データ・旧 lock の互換は対象外。障害回復と新 lock の実装を行う（O02/O09/O13）。 [#5](https://github.com/soramikan/nako-registry/issues/5) |
| #6 非公開パッケージ | 認証付き取得、権限とキャッシュ分離を後続で設計。 | 初版は公開パッケージのみ。非公開配布は後続設計とする（O17）。 [#6](https://github.com/soramikan/nako-registry/issues/6) |

lnako Issue #57 の本文は作者の GitHub Releases とレジストリ自動登録を初期経路とし、公開 transport を中央 API に差し替えられるようにする計画を記す。指示書が言及する旧中央 publication API の設計書本体は配布された作業資料と固定版の仕様ツリーには見当たらなかった。今回の対照では、固定版の実装と三文書、公開 Issue 本文を根拠にした。 [lnako #57](https://github.com/soramikan/lnako/issues/57)
