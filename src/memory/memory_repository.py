from src.memory.database import Database


class MemoryRepository:

    def __init__(self, database=None):
        self.database = database or Database()

    # Lưu danh sách memories
    
    # Lưu danh sách memories
    def save_memories(
        self,
        memories: list[dict],
        source_conversation_id: int | None = None
    ) -> int:

        saved_count = 0

        # Những chủ thể hợp lệ
        valid_subjects = {
            "user",
            "stheno",
            "other",
            "unknown"
        }

        with self.database.connect() as conn:

            for memory in memories:

                subject = memory.get("subject", "unknown")
                category = memory.get("category")
                content = memory.get("content")
                importance = memory.get("importance")

                # Kiểm tra subject
                if not isinstance(subject, str):
                    continue

                subject = subject.strip().lower()

                if subject not in valid_subjects:
                    continue

                # Kiểm tra category
                if not isinstance(category, str) or not category.strip():
                    continue

                # Kiểm tra content
                if not isinstance(content, str) or not content.strip():
                    continue

                # Kiểm tra importance
                if type(importance) is not int or not 1 <= importance <= 5:
                    continue

                category = category.strip()
                content = content.strip()

                # Kiểm tra memory đã tồn tại chưa
                existing = conn.execute(
                    """
                    SELECT id
                    FROM memories
                    WHERE subject = ?
                    AND category = ?
                    AND content = ?
                    LIMIT 1
                    """,
                    (subject, category, content)
                ).fetchone()

                if existing:
                    continue

                # Lưu memory mới
                conn.execute(
                    """
                    INSERT INTO memories (
                        subject,
                        category,
                        content,
                        importance,
                        source_conversation_id
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        subject,
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
                SELECT
                    id,
                    subject,
                    category,
                    content,
                    importance,
                    source_conversation_id,
                    created_at,
                    updated_at
                FROM memories
                ORDER BY importance DESC, id DESC
                """
            ).fetchall()

            return [dict(row) for row in rows]
