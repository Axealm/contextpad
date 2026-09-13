from app.extractor import ContextExtractor
from app.models import EmailLink


def test_extracts_context_from_japanese_work_memo():
    extractor = ContextExtractor()
    email = EmailLink(
        subject="9/17 取引先A打ち合わせについて",
        sender="contact@example.invalid",
        snippet="9/17 14:00からオンラインで取引先Aとの打ち合わせです。前日までに資料ドラフトを共有してください。",
    )
    memo = "\n".join(
        [
            "担当Aさん参加",
            "前回資料確認",
            "SaaS棚卸しのところ聞く",
            "業務ツールの利用状況も確認",
            "明日午前中ドラフト作る",
        ]
    )

    result = extractor.extract(memo, email)

    assert result.event_datetime == "9/17 14:00"
    assert result.location == "オンライン"
    assert result.deadline == "前日まで"
    assert "担当Aさん" in result.people
    assert "前回資料確認" in result.tasks
    assert "明日午前中ドラフト作る" in result.tasks
    assert result.confidence >= 0.8
