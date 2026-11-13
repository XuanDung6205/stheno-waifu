
from src.brain.ollama_client import chat
from src.memory.repository import ConversationRepository


class Conversation:

    def __init__(
        self,
        max_history_turns: int = 10,
        repository=None
    ):

        if max_history_turns < 1:
            raise ValueError(
                "max_history_turns must be positive"
            )

        self.repository = (
            repository or ConversationRepository()
        )

        self.max_messages = max_history_turns * 2

        # Khôi phục cuộc trò chuyện gần nhất để thêm mess mới vào sau này
        self.conversation_id = (
            self.repository.get_latest_conversation_id()
        )

        # Chưa có cuộc trò chuyện nào
        if self.conversation_id is None:

            self.conversation_id = (
                self.repository.create_conversation()
            )

        # Load history từ 1 cuộc hội thoại đã tắt từ trước trong SQLite
        self.messages = (
            self.repository.get_recent_messages(
                self.conversation_id,
                self.max_messages
            )
        )

        print(
            f"[MEMORY] Restored {len(self.messages)} messages"
        )

    # Gửi tin nhắn
    def send(self, message: str) -> str:

        if not message.strip():
            raise ValueError(
                "Message cannot be empty!"
            )

        print("[CONVERSATION DEBUG]")
        print("Conversation ID:", self.conversation_id)
        print("History length:", len(self.messages))

        # Gửi history cho Ollama
        result = chat(
            message,
            self.messages
        )

        # Validate JSON response
        if not isinstance(result, dict):
            raise TypeError(
                "Chat response must be a dictionary!"
            )

        assistant_content = result.get("content")
        memories = result.get("memories")

        if not isinstance(assistant_content, str):
            raise TypeError(
                "Invalid assistant content!"
            )

        if not assistant_content.strip():
            raise ValueError(
                "Assistant content cannot be empty!"
            )

        if not isinstance(memories, list):
            raise TypeError(
                "Invalid memories format!"
            )

        # Lưu cả user và assistant vào SQLite
        self.repository.save_exchange(
            self.conversation_id,
            message,
            assistant_content
        )

        # Cập nhật RAM (gửi lại lịch sử cho waifu như cũ)
        self.messages.extend([
            {
                "role": "user",
                "content": message
            },
            {
                "role": "assistant",
                "content": assistant_content
            }
        ])

        # Giới hạn history gửi cho AI
        if len(self.messages) > self.max_messages:

            self.messages = self.messages[
                -self.max_messages:
            ]

        # Trả về cả content và memories
        return {
            "content": assistant_content.strip(),
            "memories": memories
        }

    # Bắt đầu cuộc trò chuyện mới
    def reset(self, title: str):

        # tạo mới conversation_id
        self.conversation_id = (
            self.repository.create_conversation(title)
        )

        self.messages.clear()

    # Lấy bản sao lịch sử
    def get_history(self):

        return self.messages.copy()
