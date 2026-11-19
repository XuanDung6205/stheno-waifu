
import json
from pathlib import Path

from src.brain.ollama_client import (
    load_settings,
    _send_request,
    _get_content
)


ROOT_DIR = Path(__file__).resolve().parents[2]


class SubjectResolver:

    VALID_SUBJECTS = {
        "user",
        "stheno",
        "other",
        "unknown",
        "none"
    }

    def __init__(self):
        self.settings = load_settings()

        self.model = self.settings["ollama"]["memory"]["model"]

        self.prompt_path = (
            ROOT_DIR / "prompts" / "subject_resolver.txt"
        )

        if not self.prompt_path.exists():
            raise FileNotFoundError(
                f"Subject resolver prompt not found: {self.prompt_path}"
            )

        self.system_prompt = self.prompt_path.read_text(
            encoding="utf-8"
        )

    def resolve(
        self,
        message: str,
        history: list[dict] | None = None
    ) -> dict:

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty!")

        # Chỉ lấy 10 tin nhắn gần nhất.
        history_data = []

        for item in (history or [])[-10:]:

            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content")

            if role not in ("user", "assistant"):
                continue

            if not isinstance(content, str) or not content.strip():
                continue

            history_data.append({
                "role": role,
                "content": content.strip()
            })

        user_data = {
            "current_message": message.strip(),
            "conversation_history": history_data
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        user_data,
                        ensure_ascii=False
                    )
                }
            ],
            "stream": False,
            "think": False,
            "format": "json",
            "options": {
                "temperature": 0
            }
        }

        result = _send_request(payload)
        raw_content = _get_content(result)

        try:
            output = json.loads(raw_content)

        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"Subject resolver returned invalid JSON: {raw_content}"
            ) from error

        if not isinstance(output, dict):
            raise RuntimeError(
                "Invalid subject resolver output!"
            )

        # Validate subject_id
        subject_id = output.get("subject_id")

        if not isinstance(subject_id, str):
            raise RuntimeError(
                "Invalid subject_id!"
            )

        subject_id = subject_id.strip().lower()

        if subject_id not in self.VALID_SUBJECTS:
            raise RuntimeError(
                f"Unknown subject: {subject_id}"
            )

        # Validate subject_description
        description = output.get("subject_description")

        if not isinstance(description, str):
            raise RuntimeError(
                "Invalid subject description!"
            )

        description = description.strip()

        if subject_id == "none" and description:
            raise RuntimeError(
                "Subject description must be empty when subject_id is none!"
            )

        if subject_id == "other" and not description:
            raise RuntimeError(
                "Subject description cannot be empty for other!"
            )

        # Validate confidence
        confidence = output.get("confidence")

        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
        ):
            raise RuntimeError(
                "Invalid confidence!"
            )

        # Validate reason
        reason = output.get("reason")

        if not isinstance(reason, str) or not reason.strip():
            raise RuntimeError(
                "Invalid reason!"
            )

        print("\n========== SUBJECT RESOLVER DEBUG ==========")
        print(f"Selected Subject : {subject_id}")
        print(f"Description      : {description}")
        print(f"Confidence       : {float(confidence):.2%}")
        print(f"Reason           : {reason.strip()}")
        print("============================================")

        return {
            "subject_id": subject_id,
            "subject_description": description,
            "confidence": float(confidence),
            "reason": reason.strip()
        }
