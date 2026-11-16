
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
