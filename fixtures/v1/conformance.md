# v1 適合性フィクスチャ

各行を一つのケースとして使う。実装時はこの入力と期待結果を共通で使い、各処理系やレジストリ固有の診断番号は別に対応づける。ここではケースの入力を定義する。実行した確認は [スキーマ検証記録](../../docs/schema-validation.md) を参照。

## 識別子（§1）

必須フィールドを満たす通常の新規登録要求を基準に、ID だけを変える。一般登録のケースでは、他の登録権限を満たす一般利用者を使う。

| ID | 入力と操作 | 期待結果 |
| --- | --- | --- |
| ID-01 | `@soramikan/http` と `@a1/pkg-2` を別々に一般登録。 | 受理。両方とも文字、長さ、登録条件に合致。 |
| ID-02 | `http` を解釈。 | 拒否。スコープがない。 |
| ID-03 | `@Std/pkg` を解釈。 | 拒否。大文字を含む。 |
| ID-04 | `@std/foo` を一般登録。その後、存在する `@std/json` を依存として入力。 | 一般登録は予約スコープのため拒否。依存の ID としては受理。 |
| ID-05 | `@a--b/c`、`@ab-/c`、`@ab/c-`、`@ab/c--d` を別々に解釈。 | 拒否。連続または末尾のハイフンを含む。 |
| ID-06 | `1.2.0-rc.1`、`01.2.0`、`1.2.0-01`、`1.2.0+rev` を公開バージョンとして検証。 | 最初は受理。残りは先頭ゼロまたはビルドメタデータにより拒否。 |

## ソースマニフェスト（§2）

各ケースは要件の `nako.toml` サンプルを基準に、指定した箇所だけを変える。

| ID | 入力と操作 | 期待結果 |
| --- | --- | --- |
| M-01 | 先頭の `schema_version = 1` を `schema_version = 1.0` に変更。 | 拒否。TOML 上の整数が必須。 |
| M-02 | トップレベルに `legacy = true` を追加。 | 拒否。未知のトップレベルキー。 |
| M-03 | `tls = []` を `tls = ["http3"]` に変更。 | 拒否。`tls → http3 → tls` の循環。 |
| M-04 | `exports["."]` から `binding` を省略。 | 受理。既定の入口の binding は scoped。 |

## Canonical ZIP（§3.2〜§3.5）

基準アーカイブ Z0 は次の二ファイル、UTF-8 で末尾に LF を含む `src/main.nako3`（内容は `# fixture` の一行）、および `NAKO-PKG/FILES.json` の四つの通常ファイルを持つ。

`NAKO-PKG/METADATA.toml`

```toml
schema_version = 1
[package]
id = "@example/demo"
version = "1.0.0"
license = "MIT"
capabilities = ["pure-nako"]
[artifact]
kind = "universal"
runtimes = ["lnako", "cnako", "wnako"]
[exports]
"." = { entry = "src/main.nako3", binding = "scoped" }
```

`NAKO-PKG/COMMANDS.json`

```json
{
  "schema_version": 1,
  "exports_global_commands": false,
  "exports": {".": {"binding": "scoped", "commands": [], "constants": []}}
}
```

`FILES.json` は schema 版 1 とする。ほかの三つの通常ファイルの相対パス、実バイト長、SHA-256 を列挙し、パスを昇順に並べる。ZIP の方式は STORED、タイムスタンプは全件 `1980-01-01 00:00:00`、エントリを UTF-8 バイト順に並べる。ディレクトリエントリの扱いを決めた後は、同じ通常ファイルに対してその規則も適用する（O06）。各異常系では表が指定する条件を変え、ほかの検査が先に失敗しないように整える。

| ID | 入力と操作 | 期待結果 |
| --- | --- | --- |
| Z-01 | Z0 を公開前と展開前の検証に渡す。 | 受理。昇順、固定時刻、三つの制御ファイル、索引とバイト列がそろう。 |
| Z-02 | パス検査器に相対パスの禁止例 `../evil` を渡す。 | 拒否。`..` セグメントを含む。 |
| Z-03 | エントリ種別検査に通常ファイル集合とシンボリックリンク1件を渡す。 | 拒否。シンボリックリンクを含む。 |
| Z-04 | ファイル名集合の検査に `A.txt` と `a.txt` を渡す。 | 拒否。大小文字を無視すると名前が衝突する。 |
| Z-05 | Z0 の `src/main.nako3` を別の同じ長さの内容とし、索引は元の値を使う。 | 拒否。実バイト列の SHA-256 と索引が不一致。 |
| Z-06 | Z0 に `extra.txt`（内容は UTF-8 の1バイト `x`）を追加し、索引に載せない。 | 拒否。通常ファイル集合と索引が不一致。 |
| Z-07 | 設定を既定値にして、結果が `100 MiB + 1` バイトになる入力を展開量検査へ渡す。 | 上限を超える最初の時点で中断し、拒否。 |
| Z-08 | Z0 の一つのファイルの DOS 日時を `1980-01-02 00:00:00` とする。 | 拒否。固定日時が異なる。 |
| Z-09 | Z0 の `COMMANDS.json` に `./client` の scoped エントリを追加し、ファイル索引を更新する。 | 拒否。METADATA と COMMANDS のキー集合が不一致。 |
| Z-10 | Z0 の `COMMANDS.json` の `exports_global_commands` だけを `true` にし、ファイル索引を更新する。 | 拒否。global の `binding` が存在しない。 |

## Sparse Index の条件付き取得（§4.1）

| ID | 入力と操作 | 期待結果 |
| --- | --- | --- |
| I-01 | `GET /index/v1/config.json` と `GET /index/v1/packages/soramikan/http.json`。サーバーに要件のサンプルを配置する。 | 受理。設定とパッケージの JSON がそれぞれの schema を通る。パッケージ応答には ETag と Cache-Control がある。 |
| I-02 | I-01 のパッケージ応答が `ETag: "rev1"`。同じ URL を `If-None-Match: "rev1"` 付きで再取得する。続いて版一覧を更新する。 | 更新前は 304 で既存の一覧を再利用する。更新後は新しい ETag と本文を受け取る。 |

## 一括公開時のクロス検証（§5）

基準 C0 は `@example/demo` の `1.0.0` の未公開リリース。権限とクォータの条件を満たし、依存 `{id: "@example/base", req: "^1.0.0", features: [], default_features: true, optional: false}` を両方の `METADATA.toml` に記録する。registry には `@example/base` の非 yank `1.1.0` が存在する。

- U は Z0 を基に、上記の依存を追加した `universal`。
- P は U と同じ共通データに `artifact.kind = "native-prebuilt"`、`runtimes = ["lnako"]`、`artifact.native = { target_triple = "x86_64-linux-gnu", abi_version = 1, glibc_min = "2.31", library_path = "native/libdemo.so" }` を持つ。ライブラリファイルを収録する。ZIP とクロス検証の単体ケースではライブラリの内容を固定ダミーデータとして扱う。
- 各 ZIP の索引、multipart のファイル名・申告ハッシュはその入力の実体から用意する。中央 upload に U と P を含め、外部参照は空。差異を入れるケースでは関連する索引と申告ハッシュを作り直す。

| ID | 入力と操作 | 期待結果 |
| --- | --- | --- |
| X-01 | C0 で U と P を一括公開。 | 受理。同一版に二つの種別が登録される。 |
| X-02 | P だけ `req = "^2.0.0"` に変更。 | 拒否。依存の共通項目が一致しない。DB・ストレージ・index は要求前と同じ。 |
| X-03 | P だけ `./extra` を `exports` に追加し、P 内の COMMANDS も合わせる。 | 拒否。アーカイブ内は整合しているが、U と P の exports が異なる。DB・ストレージ・index は要求前と同じ。 |
| X-04 | P と同じ kind・runtimes・triple・ABI を持つ別ファイル P2 を追加。P2 の ZIP は正しく、ライブラリのバイトのみ異なる。 | 拒否。アーティファクトの組が重複する。 |
| X-05 | C0 の依存先 `@example/base` の `1.1.0` を yank。ほかに適合する版は置かない。 | 拒否。範囲を満たす非 yank 版がない。 |
| X-06 | C0 の成功後、同じバイト列で同じリリースを再送。既存版が yank 済みの場合も実施。 | どちらも `409 Conflict`。既存リリースの内容が変わらない。 |
| X-07 | C0 の U の申告ハッシュだけを別の構文上有効な値にする。 | 拒否。ストレージへの書き込み前に不一致を検出する。 |
| X-08 | C0 のインデックス置き換えが一度失敗し、次に成功するストレージを使う。 | 非同期リトライで両アーティファクトを含む index に収束する。初回応答と確定点は O09 が解決した後に固定する。 |
| X-09 | 公開先 ID に権限のない不変 `repository_id = "456"` の CI。許可 ID は `"123"`。 | 交換または権限検査で拒否し、公開状態が変わらない。応答の詳細は O11。 |
| X-10 | C0 でアクティブなファイルサイズ上限を U の実バイト長より1バイト小さく設定。 | 拒否。クォータ超過で公開状態が変わらない。 |
| X-11 | C0 の URL と JSON の ID を `@example/other` に変更し、中身を変えない。呼出元は両方に権限を持つ。 | 拒否。アーカイブの `package.id` と要求が不一致。 |

## スコープ・命令・バージョン（§6.1・§6.2）

表の import は解決器へ渡す指定名を表す。実際のなでしこソース構文は各処理系に合わせる。グラフの `A → B ^1.0.0` は A が B の `^1.0.0` を要求することを表す。

| ID | 入力と操作 | 期待結果 |
| --- | --- | --- |
| R-01 | 直接依存 `@acme/json ^1.0.0` と非衝突の `@acme/http ^1.0.0`。`json` を import。 | 受理。`@acme/json` の既定入口へ解決。 |
| R-02 | 直接依存 `@acme/json ^1.0.0` と `@other/json ^1.0.0`。後者の `alias = "fast_json"`。`json` と `fast_json` を import。 | 受理。前者は `@acme/json`、後者は `@other/json`。 |
| R-03 | R-02 の alias を除き、`json` を import。 | 拒否。Ambiguous Import。同じ依存構成の `@other/json` 完全修飾指定は受理。 |
| R-04 | ルート → `@acme/left` と `@acme/right`、左 → `@acme/json ^1.0.0`、右 → `@acme/json ^2.0.0`。候補は scoped の `1.1.0` と `2.1.0`。 | 受理。左が 1.1.0、右が 2.1.0 を別々に使い、命令はそれぞれのスコープ内だけに登録される。 |
| R-05 | R-04 の両版を `exports_global_commands = true` にして、ほかは同じ。 | 拒否。単一版へ収束できない。 |
| R-06 | `@acme/left 1.0.0` と `@acme/right 1.0.0` の `global_commands` をともに `["共通取得"]` とする。 | 拒否。別パッケージ間の命令名衝突。 |
| R-07 | ルートの直接依存は `@acme/left` のみ。left の依存 `@acme/inner` をルートから `inner` および `@acme/inner` で import。 | どちらも拒否。ルートの直接依存にない。 |
| R-08 | `@acme/dsl` の global 入口を `allow_global_commands` なしで import。 | エラーまたは厳格警告。無診断での取り込みは不適合。既定の種類は O12。 |
| R-09 | `@acme/json 1.2.0` は yank、`1.1.0` は非 yank。新規に `^1.0.0` を解決。別ケースでは既存 lock が `1.2.0` を記録し、実 hash は index と lock に一致する。 | 新規では 1.2.0 を除外。既存 lock を使うケースは使用を許可し、警告。 |

## ターゲット選択（§6.3）

`P = native-prebuilt(lnako, x86_64-linux-gnu, abi=1, glibc_min=2.31)`、`S = native-source(lnako, abi=1)`、`U = universal(lnako, cnako, wnako)`、`E = esm(cnako)`、`W = esm(wnako)`。lnako の実行側は `x86_64-linux-gnu` で ABI 1 をサポートする。

| ID | 入力と操作 | 期待結果 |
| --- | --- | --- |
| T-01 | lnako glibc 2.31、配列 `[U, S, P]`。 | 受理。配列の末尾でも P が優先。 |
| T-02 | lnako glibc 2.30、配列 `[U, S, P]`。 | P を候補から除外し、S を受理してローカルビルドへ進む。 |
| T-03 | lnako glibc 2.30、配列 `[U, P]`。 | P を候補から除外し、U を受理。 |
| T-04 | wnako、配列 `[S, P]`。 | 拒否。wnako 向けの候補がない。 |
| T-05 | cnako に `[U, E]`、wnako に `[U, E, W]`、次に wnako に `[E, U]`。 | それぞれ E、W、U を選ぶ。 |
| T-06 | lnako glibc 2.30、配列 `[P]`。 | 拒否。診断に `lnako` と `x86_64-linux-gnu` を表示。 |
| T-07 | lnako glibc 2.31、対応 ABI を 2 のみに変え、配列 `[P, S, U]`。 | P と S を除外し、U を受理。 |

## 配信セキュリティ（§4.2・§6.4）

`artifact_base_url = "https://cdn.example.invalid/artifacts"`、`allowed_external_hosts = ["repo.example.invalid"]`。URL 検証とダウンロード直後のハッシュ検証までを対象にし、ZIP 展開前で観測する。ネットワーク応答は固定する。`abc` は末尾 LF なしの3バイト。正常時は index と lock の両方に `sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad` を記録する。

| ID | 入力と操作 | 期待結果 |
| --- | --- | --- |
| D-01 | `https://cdn.example.invalid/artifacts/demo.npkg`、応答 `abc`。 | 受理。中央の基底 URL 配下で双方のハッシュが一致。 |
| D-02 | `https://repo.example.invalid/demo.npkg`、応答 `abc`。 | 受理。許可外部ホストで双方のハッシュが一致。 |
| D-03 | `https://other.example.invalid/demo.npkg`、または `https://cdn.example.invalid/artifacts-old/demo.npkg`。 | 拒否。前者は許可外ホスト、後者は基底パス外。 |
| D-04 | D-01 の応答を `abd` に変更。 | 拒否。実バイト列のハッシュが異なる。展開は行わない。 |
| D-05 | `http://repo.example.invalid/demo.npkg`。 | 拒否。HTTPS が必須。 |
| D-06 | D-01 で index と実バイト列は一致。lock のハッシュ冒頭を `ba` から `bb` に変える。 | 拒否。lock との照合が失敗。展開は行わない。 |
| D-07 | D-01 の配信元が `https://other.example.invalid/demo.npkg` にリダイレクト。 | 拒否。許可外の転送先へ取得要求を送らない。 |
