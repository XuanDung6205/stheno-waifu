import io
import json
from contextlib import redirect_stdout
from unittest import TestCase
from unittest.mock import patch

from src.memory.subject import SubjectResolver


class SubjectResolverTests(TestCase):
    def setUp(self):
        self.resolver = SubjectResolver()

    def test_accepts_valid_subject_result_with_quote_from_current_message(self):
        query = "Bạn thân anh thích gì?"
        model_output = {
            "quote": "Bạn thân anh",
            "reason": "The message asks about the user's best friend.",
            "subject_id": "other",
            "subject_description": "The user's best friend",
            "confidence": 0.99,
        }

        with redirect_stdout(io.StringIO()):
            with (
                patch("src.memory.subject._send_request", return_value={}) as send,
                patch(
                    "src.memory.subject._get_content",
                    return_value=json.dumps(model_output, ensure_ascii=False),
                ),
            ):
                result = self.resolver.resolve(query)

        self.assertEqual(result["subject_id"], "other")
        self.assertEqual(result["subject_description"], "The user's best friend")
        self.assertEqual(send.call_count, 1)

        request = send.call_args.args[0]
        self.assertIn(query, request["messages"][1]["content"])

    def test_retries_and_returns_unknown_when_quote_is_not_from_current_message(self):
        model_output = {
            "quote": "Anh thích chó",
            "reason": "The message is about the user.",
            "subject_id": "user",
            "subject_description": "The user",
            "confidence": 0.9,
        }

        with redirect_stdout(io.StringIO()):
            with (
                patch("src.memory.subject._send_request", return_value={}) as send,
                patch(
                    "src.memory.subject._get_content",
                    return_value=json.dumps(model_output, ensure_ascii=False),
                ),
            ):
                result = self.resolver.resolve("Em thích gì?")

        self.assertEqual(result["subject_id"], "unknown")
        self.assertEqual(send.call_count, 2)

    def test_includes_history_only_for_ambiguous_references(self):
        history = [
            {"role": "user", "content": "Anh có một người bạn thân."},
            {"role": "assistant", "content": "Anh kể thêm về bạn ấy đi."},
        ]

        ambiguous = self.resolver._build_user_content(
            "Người đó thích gì?",
            history,
        )
        explicit = self.resolver._build_user_content(
            "Mẹ anh thích gì?",
            history,
        )

        self.assertIn("Anh có một người bạn thân.", ambiguous)
        self.assertNotIn("Anh có một người bạn thân.", explicit)
