import re

from app.models import EmailLink, ExtractedContext


TASK_MARKERS = ("確認", "作る", "共有", "整理", "聞く", "準備", "見る", "送る", "調査")


class ContextExtractor:
    def extract(self, memo: str, email: EmailLink | None = None) -> ExtractedContext:
        source = "\n".join(part for part in [email.snippet if email else "", memo] if part)
        compact = " ".join(source.split())
        tasks = self._extract_tasks(memo)
        people = self._extract_people(compact)
        event_datetime = self._extract_datetime(compact)
        location = self._extract_location(compact)
        deadline = self._extract_deadline(compact)
        summary = self._summarize(email, memo, tasks)
        confidence = self._confidence(event_datetime, location, deadline, people, tasks)

        return ExtractedContext(
            summary=summary,
            event_datetime=event_datetime,
            location=location,
            deadline=deadline,
            people=people,
            tasks=tasks,
            confidence=confidence,
        )

    def _extract_tasks(self, memo: str) -> list[str]:
        candidates = []
        for line in re.split(r"[\n。]+", memo):
            cleaned = line.strip(" ・-　\t")
            if not cleaned:
                continue
            if any(marker in cleaned for marker in TASK_MARKERS):
                candidates.append(cleaned)
        return candidates[:10]

    def _extract_people(self, text: str) -> list[str]:
        names = re.findall(r"([一-龥ぁ-んァ-ヶA-Za-z]{1,20}(?:さん|氏|様))", text)
        return list(dict.fromkeys(names))[:10]

    def _extract_datetime(self, text: str) -> str | None:
        patterns = [
            r"(\d{1,2}/\d{1,2}\s*\d{1,2}:\d{2})",
            r"(\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2})",
            r"(\d{1,2}/\d{1,2})",
            r"(\d{1,2}月\d{1,2}日)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip()
        return None

    def _extract_location(self, text: str) -> str | None:
        match = re.search(r"(?:から|に|で)([一-龥ぁ-んァ-ヶA-Za-z0-9\s]{2,30}?)(?:で|にて|との|の打ち合わせ|集合|$)", text)
        if not match:
            return None
        location = match.group(1).strip()
        stop_words = ("打ち合わせ", "会議", "ミーティング")
        for word in stop_words:
            location = location.replace(word, "")
        return location.strip() or None

    def _extract_deadline(self, text: str) -> str | None:
        patterns = [
            r"(前日まで)",
            r"(明日(?:午前中|中|まで)?)",
            r"(\d{1,2}/\d{1,2}まで)",
            r"(\d{1,2}月\d{1,2}日まで)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _summarize(self, email: EmailLink | None, memo: str, tasks: list[str]) -> str:
        if email and email.subject:
            base = f"{email.subject} に関する作業メモ"
        else:
            base = "作業メモ"
        if tasks:
            return f"{base}。次のアクションは {tasks[0]}。"
        first_line = memo.strip().splitlines()[0]
        return f"{base}。{first_line[:60]}"

    def _confidence(
        self,
        event_datetime: str | None,
        location: str | None,
        deadline: str | None,
        people: list[str],
        tasks: list[str],
    ) -> float:
        score = 0.35
        score += 0.15 if event_datetime else 0
        score += 0.15 if location else 0
        score += 0.15 if deadline else 0
        score += 0.10 if people else 0
        score += 0.10 if tasks else 0
        return min(round(score, 2), 0.95)
