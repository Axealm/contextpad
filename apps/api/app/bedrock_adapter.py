import json
import os
from typing import Any

from app.models import EmailLink, ExtractedContext


class BedrockExtractor:
    """Adapter shape for the production Bedrock integration.

    The local MVP uses ContextExtractor. This adapter documents the target
    integration boundary and keeps Bedrock-specific code out of route handlers.
    """

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")

    def build_prompt(self, memo: str, email: EmailLink | None) -> str:
        email_payload: dict[str, Any] = email.model_dump(mode="json") if email else {}
        return json.dumps(
            {
                "instruction": "Extract work context as strict JSON with summary, event_datetime, location, deadline, people, tasks, and confidence.",
                "email": email_payload,
                "memo": memo,
            },
            ensure_ascii=False,
        )

    def parse_response(self, payload: str) -> ExtractedContext:
        data = json.loads(payload)
        return ExtractedContext(**data, ai_model=self.model_id)
