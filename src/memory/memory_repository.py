from src.memory.database import Database


class MemoryRepository:

    def __init__(self, database=None):
        self.database = database or Database()

    # Lưu danh sách memories
    def save_memories(
        self,
        memories: list[dict],
        source_conversation_id: int | None = None
    ) -> int:

        saved_count = 0

        with self.database.connect() as conn:

            for memory in memories:

                category = memory.get("category")
                content = memory.get("content")
                importance = memory.get("importance")

                # Kiểm tra dữ liệu đầu vào
                if not isinstance(category, str) or not category.strip():
                    continue

                if not isinstance(content, str) or not content.strip():
                    continue

                if type(importance) is not int or not 1 <= importance <= 5:
                    continue

                category = category.strip()
                content = content.strip()

                # Kiểm tra memory đã tồn tại chưa
                existing = conn.execute(
                    """
                    SELECT id
                    FROM memories
                    WHERE category = ?
                      AND content = ?
                    LIMIT 1
                    """,
                    (category, content)
                ).fetchone()

                if existing:
                    continue

                # Lưu memory mới
                conn.execute(
                    """
                    INSERT INTO memories (
                        category,
                        content,
                        importance,
                        source_conversation_id
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        category,
                        content,
                        importance,
                        source_conversation_id
                    )
                )

                saved_count += 1

        return saved_count

    def get_memories(self) -> list[dict]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM memories
                ORDER BY importance DESC, id DESC
                """
            ).fetchall()

            return [dict(row) for row in rows]