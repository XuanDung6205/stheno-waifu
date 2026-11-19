from unittest import TestCase
from unittest.mock import patch

from src.memory.memory_retriever import MemoryRetriever


class FakeSubjectResolver:
    def __init__(self, subject_id):
        self.subject_id = subject_id
        self.calls = []

    def resolve(self, message, history):
        self.calls.append((message, history))
        return {"subject_id": self.subject_id}


class FakeMemoryRepository:
    def __init__(self, memories):
        self.memories = memories
        self.requested_subjects = []

    def get_memories(self, subject=None):
        self.requested_subjects.append(subject)
        if subject is None:
            return self.memories
        return [
            memory
            for memory in self.memories
            if memory["subject"] == subject
        ]


def make_memory(memory_id, subject="user", content="Likes cats"):
    return {
        "id": memory_id,
        "subject": subject,
        "category": "preference",
        "content": content,
        "importance": 3,
    }


class MemoryRetrieverTests(TestCase):
    def test_filters_memories_by_resolved_subject_before_reranking(self):
        repository = FakeMemoryRepository([
            make_memory(1, "user", "Likes cats"),
            make_memory(2, "other", "Best friend likes rabbits"),
        ])
        subject = FakeSubjectResolver("other")
        retriever = MemoryRetriever(repository=repository, subject=subject)

        with patch(
            "src.memory.memory_retriever.select_relevant_memory_ids",
            return_value=[2, 1],
        ) as select_ids:
            result = retriever.retrieve("Bạn thân anh thích gì?")

        self.assertEqual(repository.requested_subjects, ["other"])
        self.assertEqual(
            [memory["id"] for memory in select_ids.call_args.kwargs["candidates"]],
            [2],
        )
        self.assertEqual([memory["id"] for memory in result], [2])

    def test_ignores_unknown_and_duplicate_ids_from_reranker(self):
        repository = FakeMemoryRepository([
            make_memory(10),
            make_memory(20, content="Likes dogs"),
            make_memory(30, content="Likes birds"),
        ])
        retriever = MemoryRetriever(
            repository=repository,
            subject=FakeSubjectResolver("user"),
            max_results=2,
        )

        with patch(
            "src.memory.memory_retriever.select_relevant_memory_ids",
            return_value=[999, 20, 20, 10],
        ):
            result = retriever.retrieve("Anh thích gì?")

        self.assertEqual([memory["id"] for memory in result], [20, 10])

    def test_uses_configured_max_candidates(self):
        repository = FakeMemoryRepository([
            make_memory(memory_id, content=f"Preference {memory_id}")
            for memory_id in range(1, 26)
        ])
        retriever = MemoryRetriever(
            repository=repository,
            subject=FakeSubjectResolver("user"),
            max_candidates=23,
        )

        with patch(
            "src.memory.memory_retriever.select_relevant_memory_ids",
            return_value=[],
        ) as select_ids:
            retriever.retrieve("Anh thích gì?")

        candidates = select_ids.call_args.kwargs["candidates"]
        self.assertEqual(len(candidates), 23)

    def test_blank_query_returns_without_resolving_subject(self):
        repository = FakeMemoryRepository([make_memory(1)])
        subject = FakeSubjectResolver("user")
        retriever = MemoryRetriever(repository=repository, subject=subject)

        self.assertEqual(retriever.retrieve("   "), [])
        self.assertEqual(subject.calls, [])
        self.assertEqual(repository.requested_subjects, [])

    def test_unknown_or_none_subject_does_not_send_memories_to_reranker(self):
        for subject_id in ("unknown", "none"):
            with self.subTest(subject_id=subject_id):
                repository = FakeMemoryRepository([
                    make_memory(1, "user"),
                    make_memory(2, "stheno"),
                    make_memory(3, "other"),
                ])
                retriever = MemoryRetriever(
                    repository=repository,
                    subject=FakeSubjectResolver(subject_id),
                )

                with patch(
                    "src.memory.memory_retriever.select_relevant_memory_ids"
                ) as select_ids:
                    self.assertEqual(
                        retriever.retrieve("Người đó thích gì?"),
                        [],
                    )

                self.assertEqual(repository.requested_subjects, [])
                select_ids.assert_not_called()
