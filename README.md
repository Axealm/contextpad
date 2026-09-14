# ContextPad

メールと自由記述のメモを結び付け、日時・場所・関係者・期限・タスクを同じ画面で整理する業務支援Webアプリです。

**React / TypeScript / FastAPI / SQLite / Gmail API**

個人開発のローカル試作版です。Gmail正常系7項目の本人確認と、50件のAPI自動テストを実施しています。現在の抽出は正規表現・キーワード方式で、生成AIやAWSへの実接続はありません。

![ContextPadの架空データ画面](docs/images/workspace-desktop.png)

[ポートフォリオ概要](docs/portfolio.md) / [90秒デモ手順](docs/demo.md)

画面は架空のサンプルです。実メール・認証情報は掲載していません。アプリを外部から操作できる公開デモではなく、コード・画面・設計・検証記録を紹介する作品です。

## 解決したい課題

メールに届いた依頼と自分のメモが分散すると、作業を再開するたびに「いつ・どこで・誰と・何をするか」を探し直す必要があります。ContextPadは入力フォームを増やさず、メール1件と自由記述のメモを結び付け、原文と整理結果を並べて確認できるようにしました。

## 作品の見どころ

| 観点 | 実装と確認 | 詳細 |
| --- | --- | --- |
| 外部サービス連携 | サーバー側OAuth、読み取り専用Gmail検索・詳細・選択・解除。保存後の紐づけ保持まで本人が実接続確認 | [実接続の受入記録](docs/ai-dlc/19-gmail-live-acceptance.md) |
| データを守る設計 | SQLite永続化、同一ID更新、JSONバックアップ、復元競合時は全体取消。APIで再起動・復旧を検証 | [保存設計](docs/ai-dlc/17-sqlite-persistence.md) / [復元設計](docs/ai-dlc/18-note-management.md) |
| 検証と説明可能性 | 50件のAPIテスト、Web型チェック・ビルド、仕様・ADR・人間の確認履歴。GitHub上のCI結果は公開後に確認 | [テスト・運用](docs/test-and-operations.md) / [レビュー履歴](docs/ai-dlc/12-human-review-log.md) |

利用者認証・共有・生成AI呼び出し・AWSデプロイは未実装です。削除・復元のブラウザー最終受入、Gmail再接続・異常系の追加実試験は残しています。実装済みの機能と受入済みの範囲を分けて記録しています。

## 開発の進め方

AWS AI-DLCの考え方を参考に、要求、設計、実装、テスト、運用上の判断を文書化しました。人間が課題・優先順位・費用制約を決め、Codexが設計案・コード・自動テスト・文書の作成を支援し、本人がGmail実接続を確認しています。コードをすべて手書きしたという主張ではなく、AI案の扱いと実際の人間レビューを[AI-DLC成果物](docs/ai-dlc/00-index.md)で示しています。

**費用方針（2026-09-14）:** 追加のサービス利用料0円を前提に開発します。AWS・Bedrockは設計資料と雛形に留め、課金の有効化や実デプロイは行いません。無料枠には上限があり、超過時は停止します。[無料構成と次の工程](docs/ai-dlc/16-free-development-roadmap.md)を参照してください。

## ドキュメント

最初に [ドキュメント一覧](docs/README.md) を参照してください。

- [仕様書](docs/specification.md): 利用者、機能、画面、受入条件、実装状況
- [基本・詳細設計書](docs/design.md): 構成図、データモデル、処理フロー、AWS設計案
- [API仕様書](docs/api-reference.md): エンドポイント、入出力、エラー、制約
- [テスト・運用設計書](docs/test-and-operations.md): 検証、起動・停止、運用、リリース条件
- [Gmail接続の設定手順](docs/gmail-setup.md): Google Cloudの作成、ローカル設定、接続試験
- [Gmail連携の設計・判断記録](docs/ai-dlc/15-gmail-integration.md): 認証境界、仕様、ADR、試験、残課題
- [AI-DLC成果物](docs/ai-dlc/00-index.md) / [人間のレビュー履歴](docs/ai-dlc/12-human-review-log.md)

## できること

- メモの新規作成、一覧、検索、切り替え、編集、保存、同一IDでの更新
- 関連メールの手入力、折りたたみ、編集、紐づけ解除
- Gmailの接続・検索・ページ読み込み・本文プレビュー・選択したメールの紐づけ・接続解除（認証設定が必要）
- ローカル抽出による日時・場所・人物・期限・タスク・要点の表示
- 保存した内容の確認済み管理、確認済み一覧への絞り込み
- 削除確認、保存済みメモのJSONバックアップ、上書きしない一括復元
- デスクトップと狭い画面への対応、通信失敗の表示

アプリ利用者の認証、共有、変更履歴、実際の生成AI呼び出し、AWSデプロイは未実装です。Gmail OAuthはアプリのログインとは別物です。**実業務メールを取り込んだり、ネットワークへ公開したりしないでください。** Terraformは一部リソースの雛形で、適用してもアプリ全体は稼働しません。

## フォルダー構成

```text
apps/api/            FastAPI、モデル、抽出器、テスト
apps/web/            React、TypeScript、Vite、依存ロック
infra/terraform/     AWSリソースの雛形
docs/                日本語の仕様・設計資料
docs/ai-dlc/         検討・判断・レビューの記録
.github/workflows/   CI設定
```

## ローカル起動

必要な環境: Python 3.12系、Node.js 22系、pnpm 11.19.0。依存関係はWebのpnpmロックを基準にします。以下はプロジェクトルートから、APIとWebそれぞれ別のターミナルで実行します。

API（PowerShell）:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Web:

```text
cd apps/web
pnpm install --frozen-lockfile
pnpm dev --port 5173
```

[アプリ](http://127.0.0.1:5173/) / [APIヘルス](http://127.0.0.1:8000/health) / [APIドキュメント](http://127.0.0.1:8000/docs)

メモの既定保存先は `apps/api/data/contextpad.sqlite3`。設定なしで初回起動時に作成され、Gitには含まれません。`apps/api/.env` の `CONTEXTPAD_DB_PATH` で変更でき、相対パスは `apps/api` 基準です。DBは暗号化されていないため、架空データ専用として扱います。[SQLite保存設計](docs/ai-dlc/17-sqlite-persistence.md)を参照してください。

Gmail未設定でも手入力の架空メールでメモの作成・整理・保存を試せます。Gmailを利用する場合は[設定手順](docs/gmail-setup.md)に従って自分のOAuthクライアントを設定します。認証情報はGitに含みません。連携トークンはメモリ内のみで、API再起動後は再接続が必要です。

APIの既定接続先は `http://127.0.0.1:8000`。`VITE_API_BASE` で変更できます。`apps/web/.env.example` は設定例で、秘密情報は入れません。Webのポートを変える場合はAPIのCORS許可も合わせて変更します。

`index.html` はファイルとして直接開かず、サーバーのURLから開きます。確認用に `dist` を配信する場合、コード変更後は `pnpm build` とブラウザーの再読み込みが必要です。停止はそれぞれのターミナルでCtrl+Cを押します。

## バックアップ

左下のダウンロードアイコンから保存済みメモをJSONで書き出し、アップロードアイコンから復元できます。上限は1,000件・5MiB。未保存の変更とGmail認証情報は含みません。メモと関連メールの本文を含む平文ファイルなので、Gitや公開場所へ置かないでください。

復元は新しいIDだけを追加し、同じID・同じ内容はスキップします。同じIDで内容が違う場合は全体を取り消し、現在のメモを守ります。削除はゴミ箱を経由しません。[詳しい操作・復旧手順](docs/ai-dlc/18-note-management.md)を参照してください。

## 検証とコミット

APIは仮想環境内で `python -m pytest -q`、Webは `pnpm build` を実行します。ローカルで50件のAPIテストを通過しています。再起動、復元、競合時の全体取消、OAuth失敗・失効などを含みます。GitHub ActionsにもAPIテスト、Webビルド、Terraform検証を定義していますが、リモート上の実行は別途確認します。

依存ディレクトリ、仮想環境、DB・バックアップ、ビルド生成物、ログ、秘密情報、Terraform state・個別変数はGitに含めません。人間の指示と実装・検証はレビュー履歴へ記録し、AIが人間の承認を代行して記録しない方針です。
