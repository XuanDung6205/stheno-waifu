import re

from src.brain.ollama_client import select_relevant_memory_ids
from src.memory.memory_repository import MemoryRepository
from src.memory.subject import SubjectResolver


class MemoryRetriever:

    STOPWORDS = {
        "anh", "em", "toi", "tao", "may",
        "la", "va", "cua", "cho", "voi",
        "thi", "mot", "nhung", "cac",
        "dang", "duoc", "nay", "do",
        "the", "is", "are", "the", "and"
    }

    def __init__(
        self,
        repository=None,
        max_results: int = 5,
        max_candidates: int = 50,
        subject=None
    ):

        if max_results < 1:
            raise ValueError("max_results must be positive!")

        if max_candidates < 1:
            raise ValueError("max_candidates must be positive!")

        self.repository = repository or MemoryRepository()
        self.subject = subject or SubjectResolver()

        self.max_results = max_results
        self.max_candidates = max_candidates

    # Tokenize text
    def _tokenize(self, text: str) -> set[str]:

        tokens = re.findall(
            r"[^\W_]+",
            text.casefold()
        )

        return {
            token
            for token in tokens
            if len(token) > 1
            and token not in self.STOPWORDS
        }

    # Calculate keyword relevance
    def _keyword_score(
        self,
        query: str,
        memory: dict
    ) -> int:

        query_tokens = self._tokenize(query)

        memory_text = (
            memory["category"] + " " + memory["content"]
        )

        memory_tokens = self._tokenize(memory_text)

        return len(query_tokens & memory_tokens)

    # Retrieve relevant memories
    def retrieve(
        self,
        query: str,
        history: list[dict] | None = None
    ) -> list[dict]:

        if not isinstance(query, str) or not query.strip():
            return []

        # Lịch sử chỉ dùng để cung cấp ngữ cảnh
        history = history or []

        # Resolve subject
        subject_result = self.subject.resolve(query, history)
        subject_id = subject_result["subject_id"]

        # Lấy memories theo subject
        if subject_id in {"user", "stheno", "other"}:
            memories = self.repository.get_memories(
                subject=subject_id
            )
        else:
            memories = self.repository.get_memories()

        if not memories:
            return []

        # Sắp xếp ứng viên theo mức độ trùng từ khóa (keyword)
        ranked_memories = sorted(
            memories,
            key=lambda memory: (
                self._keyword_score(query, memory),
                memory.get("importance", 1),
            ),
            reverse=True
        )

        candidates = ranked_memories[:self.max_candidates]

        try:
            selected_ids = select_relevant_memory_ids(
                user_message=query,
                history=history,
                candidates=candidates,
                max_results=self.max_results
            )

            if not selected_ids:
                return []

            # Chỉ chấp nhận ID thực sự tồn tại trong tập ứng viên
            memory_map = {
                memory["id"]: memory
                for memory in candidates
            }

            selected_memories = []

            for memory_id in selected_ids:
                if memory_id not in memory_map:
                    continue

                memory = memory_map[memory_id]

                if memory not in selected_memories:
                    selected_memories.append(memory)

                if len(selected_memories) >= self.max_results:
                    break

            return selected_memories

        except Exception as error:
            print(f"[MEMORY RETRIEVER ERROR] {error}")

            # Không đưa memory không chắc chắn vào AI.
            return []