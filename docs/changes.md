# 現行仕様・実装と新仕様の差分

[現行調査](current-state.md) を基準に数える。変更は既存契約の置き換え、新規は新たに規定する契約、廃止は新 v1 契約から外れる方式。旧パッケージ形式の後方互換性は維持しない。 [判断記録 O02](open-questions.md#o02)

## 変更（9件）

| ID | 現行 → 新 v1 | 節 |
| --- | --- | --- |
| C01 | `pkg:<32hex>` の Public ID と `@owner/name` の Human ID → スコープ必須の `@scope/name` をレジストリ上の識別子にする。scope と name の長さ、文字、末尾と連続ハイフンを検査する。 | §1.1 |
| C02 | `package.schema-version` は省略可、`package.name` 必須 → トップレベルの整数 `schema_version = 1` が必須。配布用 pack と公開時は `package.id/version/license` が必須。未知のトップレベルキーは拒否する。 | §2 |
| C03 | 取得元別依存、`[[exports]]`、OS/CPU/ABI 中心のプロファイル → 完全修飾 ID の依存表とランタイム別依存、サブパス別 `entry/binding`、ランタイム指定と配布種別別の `artifacts`。 | §2 |
| C04 | 一つの `.npkg` に source/native/ESM の候補を格納 → 種別・ターゲットごとにアーカイブを分け、版単位で集約。公開バージョンは `+...` 禁止。推奨ファイル名は scope、name、版、種別を含む。 | §1.2、§3.1 |
| C05 | STORED、ZIP ヘッダで時刻ゼロ、展開上限 1 GiB・100,000 件の実装 → DEFLATE/STORED、DOS 固定日時、圧縮後 25 MiB・展開後 100 MiB・2,000 ファイルの既定上限。同名の大文字小文字衝突も拒否。 | §3.2 |
| C06 | `METADATA.toml` に manifest の配布形、`FILES.toml` に payload のみ、フラットな `commands.json` → 単一アーティファクトの `METADATA.toml`、自己以外の全通常ファイルを照合する `FILES.json`、エクスポート別の `COMMANDS.json`。版キーは `schema_version`。 | §3.3〜§3.5 |
| C07 | 全体索引・パッケージページ・版レコードの分割取得 → 設定とパッケージ別の版一覧を静的 GET。ETag と Cache-Control を使う。 | §4 |
| C08 | Public ID ごとの単一版、環境の `pkg:` alias、source 優先 → 直接依存の完全修飾 ID と省略名。scoped の複数版共存と global の単一版への収束。ランタイム別のアーティファクト優先順位。 | §6.1〜§6.3 |
| C09 | 版レコード、lock、cache にまたがる旧取得処理 → SHA-256 は小文字の規定表記を使い、HTTPS の許可配信元で取得して index と lock の両方に照合。yank 版の既存 lock 使用には一致確認と警告が必要。 | §1.2、§4.2、§6.2・§6.4 |

## 新規（6件）

| ID | 新しい契約 | 節 |
| --- | --- | --- |
| N01 | 予約スコープの一般登録禁止、`scope_id` の配信、ランタイム識別子 `wnako` の追加、capabilities と公開日時の共通型。 | §1、§4.3 |
| N02 | GitHub OIDC JWT を JWKS で検証し、不変 `repository_id`、登録 workflow、版に一致する保護済みタグを照合して短命公開トークンに交換する。初版の公開は OIDC に限る。 | §5.1、§7 |
| N03 | CI の最終ジョブが一括 multipart POST。上限、ハッシュ、ZIP、全アーティファクトの共通項目・重複、依存に適合する非 yank 版の存在を確認。保存は不変オブジェクト → PostgreSQL → 静的索引と CDN の順。 | §5.2・§5.3 |
| N04 | 初版の公開は中央配信に限定する。許可外部 HTTPS ホストの配信形式は後続で有効にできる。 | §4.2、§5.2 |
| N05 | global 命令の取り込みを明示する `allow_global_commands` と、版・パッケージをまたぐ global 命令名の衝突検査。 | §2、§3.5、§6.1・§6.2 |
| N06 | 七つの共通スキーマと、レジストリ・クライアントで使う適合性フィクスチャ。理由と監査記録を伴う yank と索引再生成。初版は解除なし。 | §7 |

## 廃止（4件）

| ID | 新 v1 契約から外れる方式 | 置き換え |
| --- | --- | --- |
| R01 | Public ID の `pkg:<32hex>` と Human ID の二重識別、および URL 由来の仮 ID によるレジストリ登録。 | §1.1 の `@scope/name`。 |
| R02 | `package.schema-version`、旧 ZIP 制御名 `FILES.toml`・`commands.json` を新形式として出力すること。 | §2、§3 の `schema_version`、`FILES.json`、`COMMANDS.json`。 |
| R03 | 公開クライアントが artifact・版レコード・全体索引を個別に静的 PUT する経路。Releases 定期取込と attestation を新 API の必須経路とする計画。 | §5 の一括 POST とレジストリ側の検証・公開。§4 の静的 GET は新契約でも使う。 |
| R04 | 静的公開で同版・同一ハッシュなら再実行成功とする契約。 | §5.3 の公開済み版・yank 済み版への `409 Conflict`。インデックスの内部再試行は別の操作。 |
