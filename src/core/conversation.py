
from src.brain.ollama_client import chat


class Conversation:

    # Khởi tạo cuộc hội thoại
    def __init__(self, max_history_turns: int = 10):
        if max_history_turns < 1:
            raise ValueError("max_history_turns must be positive")

        self.messages = []
        self.max_messages = max_history_turns * 2

    # Gửi tin nhắn và cập nhật lịch sử
    def send(self, message: str) -> str:

        if not message.strip():
            raise ValueError("Message cannot be empty!")

        print("[CONVERSATION DEBUG]")
        print("History length:", len(self.messages))
        print("History:", self.messages)

        # Send message with previous history
        response = chat(
            message,
            self.messages
        )

        # Save user message
        self.messages.append({
            "role": "user",
            "content": message
        })

        # Save assistant response
        self.messages.append({
            "role": "assistant",
            "content": response
        })

        # Limit conversation history
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

        return response

    # Xóa lịch sử hiện tại
    def reset(self):
        self.messages.clear()

    # Lấy bản sao lịch sử
    def get_history(self):
        return self.messages.copy()
