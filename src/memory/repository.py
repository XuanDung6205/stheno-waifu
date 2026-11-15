
from src.memory.database import Database


class ConversationRepository:

    def __init__(self, database=None):

        self.database = database or Database()

    # Tạo cuộc trò chuyện mới
    def create_conversation(
        self,
        title: str
    ) -> int:

        with self.database.connect() as conn:

            cursor = conn.execute(
                """
                INSERT INTO conversations (title)
                VALUES (?)
                """,
                (title,)
            )

            return cursor.lastrowid

    # Lấy ID cuộc trò chuyện gần nhất
    def get_latest_conversation_id(self):

        with self.database.connect() as conn:

            row = conn.execute(
                """
                SELECT id
                FROM conversations
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()

            return row["id"] if row else None

    # Lấy lịch sử gần nhất
    def get_recent_messages(
        self,
        conversation_id: int,
        limit: int
    ) -> list[dict]:

        with self.database.connect() as conn:

            rows = conn.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, limit)
            ).fetchall()

            # Đảo lại để giữ đúng thứ tự hội thoại
            return [
                {
                    "role": row["role"],
                    "content": row["content"]
                }
                for row in reversed(rows)
            ]

    # Lưu một lượt hội thoại
    def save_exchange(
        self,
        conversation_id: int,
        user_message: str,
        assistant_response: str
    ):

        with self.database.connect() as conn:

            conn.execute(
                """
                INSERT INTO messages (
                    conversation_id,
                    role,
                    content
                )
                VALUES (?, 'user', ?)
                """,
                (conversation_id, user_message)
            )

            conn.execute(
                """
                INSERT INTO messages (
                    conversation_id,
                    role,
                    content
                )
                VALUES (?, 'assistant', ?)
                """,
                (conversation_id, assistant_response)
            )

            # Cập nhật thời gian và tiêu đề
            conn.execute(
                """
                UPDATE conversations

                SET
                    title = CASE
                        WHEN title = 'New conversation'
                        THEN ?
                        ELSE title
                    END,

                    updated_at = CURRENT_TIMESTAMP

                WHERE id = ?
                """,
                (user_message[:60], conversation_id)
            )

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
