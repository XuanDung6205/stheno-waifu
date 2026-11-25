
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

    # Luôn truyền 4 messages gần nhất.
    # Bao gồm cả user và assistant.
    def _build_user_content(
        self,
        message: str,
        history_data: list[dict]
    ) -> str:

        lines = []

        for item in history_data[-4:]:
            role = item["role"].upper()
            content = item["content"][:200]

            lines.append(f"{role}: {content}")

        history_text = "\n".join(lines)

        return (
            "<history>\n"
            f"{history_text}\n"
            "</history>\n\n"
            "<current_message>\n"
            f"{message.strip()}\n"
            "</current_message>"
        )

    def _call_and_validate(
        self,
        user_content: str,
        message: str
    ) -> dict:

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            "stream": False,
            "think": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_ctx": 3072,
                "num_predict": 200
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

        # Validate quote
        quote = output.get("quote")

        if not isinstance(quote, str) or not quote.strip():
            raise RuntimeError(
                "Invalid quote!"
            )

        normalize = lambda s: " ".join(s.casefold().split())

        if normalize(quote) not in normalize(message):
            raise RuntimeError(
                f"Quote not found in current message: {quote}"
            )

        print("\n========== SUBJECT RESOLVER DEBUG ==========")
        print(f"Selected Subject : {subject_id}")
        print(f"Description      : {description}")
        print(f"Confidence       : {float(confidence):.2%}")
        print(f"Reason           : {reason.strip()}")
        print(f"Quote            : {quote.strip()}")
        print("============================================")

        return {
            "subject_id": subject_id,
            "subject_description": description,
            "confidence": float(confidence),
            "reason": reason.strip(),
            "quote": quote.strip()
        }

    def resolve(
        self,
        message: str,
        history: list[dict] | None = None
    ) -> dict:

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty!")

        # Chuẩn hóa history.
        history_data = []

        for item in (history or []):

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

        # Luôn lấy 4 messages gần nhất.
        recent_history = history_data[-4:]

        user_content = self._build_user_content(
            message=message,
            history_data=recent_history
        )

        print("\n========== RESOLVER INPUT DEBUG ==========")
        print(f"History messages: {len(recent_history)}")
        print(user_content)
        print("==========================================")

        last_error = None

        # Tối đa 2 lần inference.
        # Retry vẫn giữ nguyên history.
        for attempt in range(2):

            try:
                return self._call_and_validate(
                    user_content=user_content,
                    message=message
                )

            except RuntimeError as error:
                last_error = error

                print(
                    f"[RESOLVER] Attempt {attempt + 1} failed: {error}"
                )

        # Cả hai lần đều thất bại → fallback an toàn.
        print(
            "[RESOLVER] All attempts failed. Using fallback."
        )

        return {
            "subject_id": "unknown",
            "subject_description": "",
            "confidence": 0.0,
            "reason": f"Resolver failed: {last_error}",
            "quote": ""
        }
