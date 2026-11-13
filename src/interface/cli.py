
from src.core.conversation import Conversation
import json


def main():

    conversation = Conversation(
        max_history_turns=10
    )

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
                title = input("\nNhập tên cuộc trò chuyện mới: ").strip()
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

                 # In phản hồi của Stheno
                response = conversation.send(message)

                print(f"Stheno: {response['content']}")

                 # In toàn bộ memories
                print("\n========== EXTRACTED MEMORIES ==========")
                print(json.dumps(
                    response["memories"],
                    ensure_ascii=False,
                    indent=4
                ))
                print("========================================")

                # đề dành lưu xuống database sau này
                memories = response["memories"]

            except (RuntimeError, ValueError) as error:
                print(f"\n[ERROR] {error}")

    except KeyboardInterrupt:
        print("\n\nStheno: Hẹn gặp lại anh nhé!")


if __name__ == "__main__":
    main()
