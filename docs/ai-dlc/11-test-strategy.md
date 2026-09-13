# Test Strategy

## Test Pyramid

- Unit tests for extraction parsing and validation
- API tests for request and response contracts
- UI tests for the create-and-extract flow
- Infrastructure validation for Terraform formatting and planning

## MVP Test Coverage

Required:

- Extracts tasks from rough Japanese memo lines
- Extracts date/time from email snippet or memo
- Extracts location from common phrasing
- Returns stable JSON response shape
- Rejects empty memo

## AI-Specific Test Policy

Live AI tests are not used as unit tests because model output can vary. Instead:

- Deterministic extractor is unit-tested.
- Bedrock adapter validates schema and handles malformed model output.
- Golden sample prompts are stored for manual review.

## Manual QA Scenario

Input email:

```text
9/17 14:00からオンラインで取引先Aとの打ち合わせです。
SaaS管理高度化の現状課題について整理をお願いします。
前日までに資料ドラフトを共有してください。
```

Input memo:

```text
担当Aさん参加
前回資料確認
SaaS棚卸しのところ聞く
業務ツールの利用状況も確認
明日午前中ドラフト作る
```

Expected:

- Date/time: `9/17 14:00`
- Location: `オンライン`
- People includes `担当Aさん`
- Deadline mentions previous day or draft deadline
- Tasks include previous material review, SaaS inventory question, 業務ツール usage check, draft creation
