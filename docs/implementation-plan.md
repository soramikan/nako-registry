# 実装準備メモ

この一覧は実装の着手順と各単位の完了条件を示す。仕様と試験入力は [仕様本文](specification.md)、[適合性フィクスチャ](../fixtures/v1/conformance.md) を参照。依存に挙げた単位の成果を先にそろえる。O 番号は実装時に決める論点を示す。 [未決定事項](open-questions.md)

| ID | 対象リポジトリ・モジュール | 先行 | 完了条件 | 仕様・フィクスチャ |
| --- | --- | --- | --- | --- |
| P01 | `nako-registry` の `schemas/v1` と共通フィクスチャ | なし | 7 schema と入力を固定し、TOML の JSON 写像を含めて再現可能に検証する。正式な配布元と運用上の必須欄は O01/O14。 | §1〜§5・§7、ID-01〜06、M-01〜04、Z-01・Z-09/10、全サンプル |
| P02 | 共有 `nako-pkg-core` の ID・型・manifest 検証。初期の利用側は `nako-registry`、`lnako` | P01 | ID 構文、一般登録での予約判定、公開 SemVer、hash、target、feature の循環、SPDX と範囲式を検査する。O04/O05 を確定する。 | §1〜§2、ID-01〜06、M-01〜04 |
| P03 | `nako-pkg-core` の Canonical ZIP、`lnako` の pack/verify | P02 | 全 kind の pack と厳格検証。正常 ZIP は再生成して一致を確認し、制御ファイル・実バイト列・上限の不一致を拒否する。O06/O07/O08 を確定する。 | §3、Z-01〜10 |
| P04 | `nako-pkg-core` のクロスアーティファクト検証 | P03 | 共通値、グローバル命令名、アーティファクトの重複を検査し、整合した複数種を受理する。O08 の比較規則で実装する。 | §5.3 の手順5、X-01〜04 |
| P05 | `nako-registry` の Sparse Index 生成・匿名取得 | P01、P02 | config とパッケージ別 index を生成し、ETag と条件付き GET、Cache-Control、yank 状態を固定入力で確認する。旧取得口は O02、scope ID は O03。 | §4、I-01/02、X-01・X-08、R-09、D-01/02 |
| P06 | `nako-registry` の OIDC 交換と公開権限 | P02 | JWKS で検証し、不変 repository ID と権限で交換を制御する。手動経路の provenance は unverified。O03/O11 を確定する。 | §1.1・§5.1・§7、ID-04、X-09 |
| P07 | `nako-registry` の公開 POST、PostgreSQL、S3/R2 | P03〜P06 | multipart の照合、クォータ、依存の存在、全件検証、同版の競合拒否を確認する。ストレージ/DB/index の失敗注入で公開状態と再試行を観測する。O09/O10/O11/O16 を確定する。 | §5、X-01〜11 |
| P08 | `nako-registry` の yank とインデックス更新 | P05〜P07 | 権限を確認して yank し、インデックスを更新する。既存アーティファクトの hash を保持し、公開済み版の上書きを拒否する。O15 を確定する。 | §5.3・§6.2・§7、X-06、R-09 |
| P09 | `nako-pkg-core` のターゲット選択と省略インポート表。利用側は `lnako`、`cnako`、`wnako` | P02 | 全ランタイムで優先順位を再現し、省略名の曖昧さと直接依存の境界を診断する。O07/O12 を確定する。 | §6.1・§6.3、R-01〜03・R-07、T-01〜07 |
| P10 | `lnako`、`cnako`、`wnako` のリゾルバ、命令登録、取得と lock | P03、P05、P09 | scoped の複数メジャー版、global の単一版と命令衝突、yank、HTTPS と両ハッシュの照合を同じ入力で確認する。新旧 lock は O02/O13 に従う。 | §4.2・§6、R-01〜09、T-01〜07、D-01〜07 |
| P11 | `lnako` の公開 CLI と `nako-registry` の CI 統合試験 | P07、P08、P10 | 最終 CI ジョブで複数成果物を一括公開し、index から解決、ダウンロード、検証、yank まで確認する。再送の `409` と index 内部リトライを別々に観測する。旧経路の扱いと dry-run は O02/O11 に従う。 | §3〜§7、X-01・X-06・X-08、R-09、T-01・T-02、D-01・D-06 |

共有ライブラリの実体の配置と Zig/Rust/JavaScript の接続方式は O01 と合わせて決める。リポジトリをまたぐ依存を導入する前に、同じフィクスチャで同じ入出力を照合できるようにする。
