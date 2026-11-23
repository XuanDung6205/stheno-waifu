
from src.core.conversation import Conversation
import json
# from src.voice.tts_engine import TTSEngine
from src.voice.clit import SthenoVoice

def display_memories(memories: list[dict]):
    print("\n========== EXTRACTED MEMORIES ==========")

    if not memories:
        print("[INFO] Không có thông tin mới cần ghi nhớ.")
    else:
        for index, memory in enumerate(memories, start=1):
            print(f"\nMemory #{index}")
            print(f"  Category:   {memory['category']}")
            print(f"  Subject:    {memory['subject']}")
            print(f"  Content:    {memory['content']}")
            print(f"  Importance: {memory['importance']}/5")

    print("\n========================================")


def main():

    conversation = Conversation(
        max_history_turns=10
    )

    # nói
    # tts = TTSEngine()

    OmniVoice = SthenoVoice()

    print("==============================")
    print("       STHENO CHAT")
    print("==============================")
    print("Commands:")
    print("  /reset  - Reset conversation")
    print("  /exit   - Exit application")
    print("==============================")

    try:
        while True:

            message = input("\nDũng: ").strip()

            if not message:
                continue

            command = message.lower()

            if command in ["/exit", "/quit"]:
                print("\nStheno: Tạm biệt anh nhé!")
                break

            if command == "/reset":
                title = input(
                    "\nNhập tên cuộc trò chuyện mới: "
                ).strip()

                if not title:
                    title = "New conversation"

                conversation.reset(title)

                print(
                    "\n[OK] New conversation started!"
                    " Previous history preserved."
                )
                continue

            try:
                print("\nStheno đang suy nghĩ...")

                response = conversation.send(message)

                # Display normal AI response
                print("\n========== STHENO RESPONSE ==========")
                print(f"\nStheno: {response['content']}")
                print("=====================================")

                

                # Voice output
                try:
                    # tts.speak(response["content"])

                    OmniVoice.speak(response["content"])
                except Exception as error:
                    print(f"\n[VOICE ERROR] {error}")

                # Display extracted memories
                memories = response["memories"]

                display_memories(memories)

            except (RuntimeError, ValueError, TypeError) as error:
                print(f"\n[ERROR] {error}")

    except KeyboardInterrupt:
        print("\n\nStheno: Hẹn gặp lại anh nhé!")


if __name__ == "__main__":
    main()
