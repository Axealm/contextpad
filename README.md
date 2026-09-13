# ContextPad

メールと自由記述のメモを結び付け、日時・場所・関係者・期限・タスクを同じ画面で整理する業務支援Webアプリです。

現在は **React / TypeScript + Python / FastAPI のローカル試作版** です。抽出は正規表現・キーワードによる処理で、Gmail APIやAmazon Bedrockには接続していません。保存はAPIプロセスのメモリ上のみで、再起動すると消えます。

サンプルは「取引先A」「担当Aさん」「オンライン」などの架空の表記と予約ドメインを使用します。実在する取引先、人物、案件、メールを意味しません。AWSやGmail等の技術サービス名は構成説明のため記載しています。

## ドキュメント

最初に [ドキュメント一覧](docs/README.md) を参照してください。

- [仕様書](docs/specification.md): 利用者、機能、画面、受入条件、実装状況
- [基本・詳細設計書](docs/design.md): 構成図、データモデル、処理フロー、AWS設計案
- [API仕様書](docs/api-reference.md): エンドポイント、入出力、エラー、制約
- [テスト・運用設計書](docs/test-and-operations.md): 検証、起動・停止、運用、リリース条件
- [AI-DLC成果物](docs/ai-dlc/00-index.md) / [人間のレビュー履歴](docs/ai-dlc/12-human-review-log.md)

## できること

- メモの新規作成、一覧、検索、切り替え、編集、保存、同一IDでの更新
- 関連メールの手入力、折りたたみ、編集、紐づけ解除
- ローカル抽出による日時・場所・人物・期限・タスク・要点の表示
- 保存した内容の確認済み管理、確認済み一覧への絞り込み
- デスクトップと狭い画面への対応、通信失敗の表示

認証、永続DB、削除、共有、変更履歴、Gmail OAuth、実際の生成AI呼び出し、AWSデプロイは未実装です。Terraformは一部リソースの雛形で、適用してもアプリ全体は稼働しません。

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

APIの既定接続先は `http://127.0.0.1:8000`。`VITE_API_BASE` で変更できます。`apps/web/.env.example` は設定例で、秘密情報は入れません。Webのポートを変える場合はAPIのCORS許可も合わせて変更します。

`index.html` はファイルとして直接開かず、サーバーのURLから開きます。確認用に `dist` を配信する場合、コード変更後は `pnpm build` とブラウザーの再読み込みが必要です。停止はそれぞれのターミナルでCtrl+Cを押します。

## 検証とコミット

APIは仮想環境内で `python -m pytest -q`、Webは `pnpm build` を実行します。GitHub ActionsにもAPIテスト、Webビルド、Terraform検証を定義していますが、リモート上の実行は別途確認します。

依存ディレクトリ、仮想環境、ビルド生成物、ログ、秘密情報、Terraform state・個別変数はGitに含めません。人間の指示と実装・検証はレビュー履歴へ記録し、AIが人間の承認を代行して記録しない方針です。
