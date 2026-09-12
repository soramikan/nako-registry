# nako-registry

なでしこ3共通パッケージ仕様案に基づく、静的レジストリと中央レジストリへの移行を管理するリポジトリです。lnakoでの先行実装から、cnako・wnakoでの利用へ展開する計画です。

現在は設計・実装計画をIssueへ登録した段階です。パッケージ取得API、自動登録CI、GitHub Pages配信、中央サーバーは今後実装します。

- [全体方針・段階別完了条件：lnako Package System](https://github.com/users/soramikan/projects/2)
- [共通仕様・schema・適合例の先行Issue](https://github.com/soramikan/lnako/issues/43)
- [lnakoリポジトリ](https://github.com/soramikan/lnako)

## 計画

| 段階 | 内容 |
|---|---|
| 初期の静的配布 | GitHub Pagesでインデックス、作者のGitHub Releasesでパッケージを配信 |
| 自動登録 | 所有者確認済みリポジトリの公開CIとartifact attestationを検証して登録 |
| 中央化 | Rust＋Axum、PostgreSQL、S3互換ストレージによる自前サーバーへ移行 |
| 後続 | 非公開パッケージの権限・認証・キャッシュ分離を設計 |

共通仕様・schema・適合性テストの正本は当面lnakoに置きます。全体方針の正本はProject README、各機能の受け入れ条件とテストはIssue本文です。上流なでしこ3での採用状態と実装・検証状態を区別して管理します。

## このリポジトリのIssue

| Issue | 内容 |
|---|---|
| [#1](https://github.com/soramikan/nako-registry/issues/1) | 静的レジストリ・所有者登録・共通取得API |
| [#2](https://github.com/soramikan/nako-registry/issues/2) | 信頼済み公開CIの検証とインデックス自動登録 |
| [#3](https://github.com/soramikan/nako-registry/issues/3) | 中央API・PostgreSQL・S3互換保存 |
| [#4](https://github.com/soramikan/nako-registry/issues/4) | 所有者認証・CI公開・所有権移転・yank |
| [#5](https://github.com/soramikan/nako-registry/issues/5) | 静的データ移行・旧lock検証・切替復旧・運用監視 |
| [#6](https://github.com/soramikan/nako-registry/issues/6) | 非公開パッケージの設計 |

依存関係は各Issueのblocked-by、実装段階と進捗はProjectのStage・Statusで管理します。

## 移行時に維持する契約

- 静的配信と中央APIで、レジストリ情報・版一覧・不変版情報・ハッシュによる取得場所の応答契約を共有します。
- レジストリID、パッケージID、バージョン、artifactハッシュを保持します。
- 同じ版・同じ内容の再処理は成功扱いとし、同じ版への異なる内容の上書きは拒否します。
- 初期のdiscovery URLを維持し、移行前のmanifest・lockで同じ内容を取得できることを検証します。
- 所有権移転とyankで、既存パッケージIDや配布内容を置き換えません。
- 切替前に新旧API比較、バックアップ復元、公開処理の再実行、静的配信への復帰を検証します。
