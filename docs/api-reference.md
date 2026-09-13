# ContextPad API仕様書

文書版: 0.1 / 更新日: 2026-09-13 / 対象: 現行FastAPI実装

ベースURLは `http://127.0.0.1:8000`。リクエスト・レスポンスはJSON。動的なAPI定義は `/openapi.json`、対話的なドキュメントは `/docs` で取得できる。現行版に認証や利用者分離はない。

## エンドポイント一覧

| メソッド | パス | 成功 | 処理 |
| --- | --- | --- | --- |
| GET | `/health` | 200 | `{"status":"ok"}` |
| POST | `/api/v1/extract` | 200 | メモとメールから抽出し、保存せず返す |
| POST | `/api/v1/notes` | 200 | 抽出して新規メモを作成。201ではなく200 |
| GET | `/api/v1/notes` | 200 | メモ配列。作成日時の降順 |
| GET | `/api/v1/notes/{note_id}` | 200 | 単一WorkNote。不明IDは404 |
| PUT | `/api/v1/notes/{note_id}` | 200 | メモを全体更新。ID・created_atは維持、不明IDは404 |
| POST | `/api/v1/notes/{note_id}/review` | 200 | 抽出結果全体を確認済みにする。不明IDは404 |

DELETE、ページング、共有、OAuthコールバック、Gmail検索、項目別承認のAPIは未実装。

## 作成・更新の入力

以下は架空のメール例。PUTも同じ形の入力を使い、省略したemailはnullになる。部分更新のPATCHではない。

```json
{
  "title": "9/17 取引先A 打ち合わせ",
  "memo": "担当Aさん参加\n前回資料確認\n明日午前中ドラフト作る",
  "email": {
    "provider": "gmail",
    "provider_message_id": null,
    "subject": "9/17 取引先A打ち合わせについて",
    "sender": "contact@example.invalid",
    "received_at": null,
    "snippet": "9/17 14:00からオンラインで取引先Aとの打ち合わせです。前日までに資料ドラフトを共有してください。"
  }
}
```

title・memoは必須かつ1文字以上。emailは任意。providerはgmailのみ。subject・sender・snippetは空文字を許可する。入力の最大長、空白だけのAPI入力、余分なフィールドの厳密な拒否は現行モデルで十分に制約されていない。UIは空白だけの本文を保存・整理できないようにしている。

## WorkNoteレスポンス

```json
{
  "id": "00000000-0000-4000-8000-000000000001",
  "title": "9/17 取引先A 打ち合わせ",
  "memo": "担当Aさん参加\n前回資料確認\n明日午前中ドラフト作る",
  "email": {
    "provider": "gmail",
    "provider_message_id": null,
    "subject": "9/17 取引先A打ち合わせについて",
    "sender": "contact@example.invalid",
    "received_at": null,
    "snippet": "9/17 14:00からオンラインで取引先Aとの打ち合わせです。前日までに資料ドラフトを共有してください。"
  },
  "context": {
    "summary": "9/17 取引先A打ち合わせについて に関する作業メモ。次のアクションは 前回資料確認。",
    "event_datetime": "9/17 14:00",
    "location": "オンライン",
    "deadline": "前日まで",
    "people": ["担当Aさん"],
    "tasks": ["前回資料確認", "明日午前中ドラフト作る"],
    "confidence": 0.95,
    "ai_model": "local-deterministic-extractor",
    "review_status": "ai_generated"
  },
  "created_at": "2026-09-13T00:00:00Z",
  "updated_at": "2026-09-13T00:00:00Z"
}
```

ID・時刻は説明用の値。実際はサーバーが生成する。contextの各項目は[基本・詳細設計書](design.md)を参照。

## 抽出・一覧・確認

`POST /api/v1/extract` の入力は上記からtitleを除いた `{ "memo": "...", "email": ... }`。出力はcontextオブジェクトのみで、新規IDは作らない。

`GET /api/v1/notes?query=取引先A` はtitle・memo・email.subject・context.tasksを大文字小文字を区別せず部分一致検索する。空または省略時は全件。人物・場所の独立した構造化フィールドやsenderは直接検索しない。

`POST /api/v1/notes/{note_id}/review` の本文は不要。review_statusをhuman_reviewedにしてupdated_atを更新する。APIにはレビュアーの身元や確認イベントは記録されない。

## エラーと制約

不明IDの例:

```json
{"detail":"note not found"}
```

型違い・必須項目不足・空文字には422と、FastAPI/Pydantic標準の `detail` 配列を返す。要素にはloc・msg・type等が入り、詳細はライブラリ版に依存する。初期設計の `{ "error": { "code": ... } }` 形式は未実装。

通信断・タイムアウト・JSON解析失敗は画面側が通知する。POSTの冪等性キー、楽観ロック、リクエスト上限、レート制限は未実装。タイムアウト時にサーバーの保存自体が完了している場合を、現行UIは識別できない。
