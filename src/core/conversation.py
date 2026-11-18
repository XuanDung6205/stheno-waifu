
from src.brain.ollama_client import chat, extract_memories
from src.memory.conversation_repository import ConversationRepository
from src.memory.memory_repository import MemoryRepository
from src.memory.memory_retriever import MemoryRetriever

class Conversation:

    def __init__(
        self,
        max_history_turns: int = 10,
        conversationRepository=None,
        memoryRepository=None,
        Memory_Retriever=None
    ):

        if max_history_turns < 1:
            raise ValueError(
                "max_history_turns must be positive"
            )

        self.conversationRepository = (
            conversationRepository or ConversationRepository()
        )

        self.MemoryRetriever = (
            Memory_Retriever or MemoryRetriever()
        )

        self.memoryRepository = (
                    memoryRepository or MemoryRepository()
                )

        self.max_messages = max_history_turns * 2

        # Khôi phục cuộc trò chuyện gần nhất để thêm mess mới vào sau này
        self.conversation_id = (
            self.conversationRepository.get_latest_conversation_id()
        )

        # Chưa có cuộc trò chuyện nào
        if self.conversation_id is None:

            self.conversation_id = (
                self.conversationRepository.create_conversation("New conversation")
            )

        # Load history từ 1 cuộc hội thoại đã tắt từ trước trong SQLite
        self.messages = (
            self.conversationRepository.get_recent_messages(
                self.conversation_id,
                self.max_messages
            )
        )

        print(
            f"[MEMORY] Restored {len(self.messages)} messages"
        )

    # Gửi tin nhắn
    
    def send(self, message: str) -> dict:

        if not message.strip():
            raise ValueError("Message cannot be empty!")

        print("\n[CONVERSATION DEBUG]")
        print("Conversation ID:", self.conversation_id)
        print("History length:", len(self.messages))

        # lấy memories liên quan dựa vào mess hiện tại và lịch sử mess trong hội thoại này trước đó
        memory_list_from_pass = self.MemoryRetriever.retrieve(
            query=message,
            history=self.messages
        )

        # Debug retrieved memories
        print("\n========== RETRIEVED MEMORIES ==========")
        if memory_list_from_pass:
            for index, memory in enumerate(memory_list_from_pass, start=1):
                print(f"\n[{index}] Memory ID: {memory.get('id', 'N/A')}")
                print(f"    Category:    {memory.get('category', 'N/A')}")
                print(f"    Subject:    {memory['subject']}")
                print(f"    Importance:  {memory.get('importance', 'N/A')}")
                print(f"    Content:     {memory.get('content', 'N/A')}")
        else:
            print("No relevant memories found.")
        print("========================================\n")


        # Request 1: Normal conversation
        assistant_content = chat(
            message=message,
            history=self.messages,
            memories=memory_list_from_pass
        )

        if not isinstance(assistant_content, str):
            raise TypeError("Invalid assistant content!")

        if not assistant_content.strip():
            raise ValueError("Assistant content cannot be empty!")

        # Request 2: Memory extraction
        memories = []

        try:
            memory_result = extract_memories(message)
            memories = memory_result["memories"]

            saved_count = self.memoryRepository.save_memories(
                memories=memories,
                source_conversation_id=self.conversation_id
            )

            print(f"[MEMORY] Extracted: {len(memories)}")
            print(f"[MEMORY] Saved: {saved_count}")
            # print("DANH SÁCH MEMORY:")
            # memories = self.memoryRepository.get_memories()
            # for memory in memories:
            #     print(memory)

        except Exception as error:
            # Memory extraction failure should not break chatting
            print(f"[MEMORY ERROR] {error}")

        # Save conversation
        self.conversationRepository.save_exchange(
            self.conversation_id,
            message,
            assistant_content
        )

        # Update RAM history
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

        # Limit conversation history
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

        return {
            "content": assistant_content.strip(),
            "memories": memories
        }


    # Bắt đầu cuộc trò chuyện mới
    def reset(self, title: str):

        # tạo mới conversation_id
        self.conversation_id = (
            self.conversationRepository.create_conversation(title)
        )

        self.messages.clear()

    # Lấy bản sao lịch sử
    def get_history(self):

        return self.messages.copy()
