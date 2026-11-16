import re

from src.brain.ollama_client import select_relevant_memory_ids
from src.memory.memory_repository import MemoryRepository


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
        max_candidates: int = 60
    ):

        if max_results < 1:
            raise ValueError("max_results must be positive!")

        if max_candidates < 1:
            raise ValueError("max_candidates must be positive!")

        self.repository = repository or MemoryRepository()

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
    def retrieve(self, query: str) -> list[dict]:

        if not isinstance(query, str) or not query.strip():
            return []

        memories = self.repository.get_memories()

        if not memories:
            return []

        # Step 1: Keyword Search
        ranked_memories = sorted(
            memories,
            key=lambda memory: (
                self._keyword_score(query, memory),
                memory.get("importance", 1),
                memory.get("id", 0)
            ),
            reverse=True
        )

        # Step 2: Build candidate pool
        candidates = ranked_memories[:self.max_candidates]

        # Step 3: AI Reranking
        try:

            selected_ids = select_relevant_memory_ids(
                user_message=query,
                candidates=candidates,
                max_results=self.max_results
            )

            memory_map = {
                memory["id"]: memory
                for memory in candidates
            }

            selected_memories = [
                memory_map[memory_id]
                for memory_id in selected_ids
                if memory_id in memory_map
            ]

            if selected_memories:
                return selected_memories

        except Exception as error:

            print(
                f"[MEMORY RETRIEVER ERROR] {error}"
            )

        # Step 4: Keyword fallback
        return [
            memory
            for memory in ranked_memories
            if self._keyword_score(query, memory) > 0
        ][:self.max_results]