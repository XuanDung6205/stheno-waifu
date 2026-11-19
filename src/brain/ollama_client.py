import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# Xác định thư mục gốc của project
ROOT_DIR = Path(__file__).resolve().parents[2]


def load_settings():
    config_path = ROOT_DIR / "config" / "settings.json"
    

    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def check_ollama():
    settings = load_settings()

    base_url = settings["ollama"]["base_url"].rstrip("/")
    model_names = {
        settings["ollama"]["chat"]["model"],
        settings["ollama"]["memory"]["model"]
    }

    url = f"{base_url}/api/tags"

    request = Request(
        url,
        headers={"Accept": "application/json"}
    )

    try:
        with urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

    except (URLError, TimeoutError) as error:
        print("[ERROR] Cannot connect to Ollama!")
        print(f"Details: {error}")
        return False

    models = [
        model["name"]
        for model in data.get("models", [])
    ]

    print("[OK] Ollama server is running!")

    # if model_name not in models:
    #     print(f"[ERROR] Model not found: {model_name}")
    #     print("Available models:")

    #     for model in models:
    #         print(f" - {model}")

    #     return False

    # print(f"[OK] Model found: {model_name}")

    for model_name in model_names:
        if model_name not in models:
            print(f"[ERROR] Model not found: {model_name}")
            return False

    print(f"[OK] Model found: {model_name}")

    return True


def _send_request(payload: dict, timeout: int = 180) -> dict:
    settings = load_settings()
    base_url = settings["ollama"]["base_url"].rstrip("/")

    request = Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Ollama HTTP Error {error.code}: {details}"
        ) from error

    except URLError as error:
        raise RuntimeError(
            f"Cannot connect to Ollama: {error.reason}"
        ) from error

    except TimeoutError as error:
        raise RuntimeError(
            "Ollama response timed out!"
        ) from error

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Ollama returned invalid JSON!"
        ) from error


def _get_content(result: dict) -> str:
    content = result.get("message", {}).get("content")

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Ollama returned an empty response!")

    return content.strip()


def chat(message: str, history: list[dict] | None = None, memories: list[dict] | None = None) -> str:
    """
    Send conversation history and memories then get a normal text response.
    """

    if not message.strip():
        raise ValueError("Message cannot be empty!")

    settings = load_settings()
    model_name = settings["ollama"]["chat"]["model"]
    
    messages = []

    # 2. Memory Context
    if memories:
        memory_context = "\n".join(
            f"""
            - Subject: {memory.get('subject', 'unknown')}
            Category: {memory['category']}
            Content: {memory['content']}
            Importance: {memory['importance']}/5
            """
            for memory in memories
        )

        messages.append({
            "role": "system",
            "content": f"""
    # LONG-TERM MEMORY

    Dưới đây là những ký ức được truy xuất từ cơ sở dữ liệu.
    Mỗi ký ức đều có subject xác định đối tượng mà nó mô tả.

    {memory_context}

    ## SUBJECT DEFINITIONS

    - user: Anh Dũng (tôi), người đang trò chuyện với em (bạn).
    - stheno: Chính em, Stheno.
    - other: Một người hoặc thực thể khác.
    - unknown: Chưa xác định được đối tượng.

    ## MEMORY INTERPRETATION RULES

    1. Subject là thông tin bắt buộc phải tuân thủ.

    2. Nếu subject = user:
    - Đây là thông tin về anh Dũng.
    - Không được nhận đó là sở thích hoặc trải nghiệm của em.

    3. Nếu subject = stheno:
    - Đây là thông tin về chính em, Stheno.
    - Hãy xem nó như ký ức và sở thích của bản thân em.
    - Khi nhắc đến, hãy sử dụng ngôi thứ nhất "em".
    - Không được chuyển thông tin này thành sở thích của anh Dũng.

    4. Nếu subject = other:
    - Đây là thông tin về một người hoặc thực thể khác.
    - Không được gán thông tin đó cho anh hoặc cho em.

    5. Nếu subject = unknown:
    - Không tự suy đoán đối tượng.
    - Không sử dụng ký ức này để khẳng định thông tin cá nhân.

    ## GENERAL RULES

    - Ký ức là thông tin từ những cuộc trò chuyện trước.
    - Sử dụng ký ức tự nhiên khi chúng thực sự liên quan.
    - Không đọc lại nguyên văn cơ sở dữ liệu.
    - Không giả vờ rằng anh vừa nhắc lại thông tin cũ.
    - Không suy diễn thêm những sở thích chưa được xác nhận.
    - Nếu ký ức không đủ thông tin, hãy thành thật thừa nhận.
    """
        })

    # 3. Conversation History
    messages.extend(history or [])

    messages.append({
        "role": "user",
        "content": message
    })


    payload = {
        "model": model_name,
        "messages": messages,
        "think": False,
        "stream": False
    }

    result = _send_request(payload)

    print("\n========== CHAT TOKEN USAGE ==========")
    print("Input tokens:", result.get("prompt_eval_count", 0))
    print("Output tokens:", result.get("eval_count", 0))
    print("======================================")

    return _get_content(result)



def extract_memories(user_message: str) -> dict:
    """
    Extract memories from the latest user message only.
    """

    if not isinstance(user_message, str) or not user_message.strip():
        raise ValueError("Message cannot be empty!")

    settings = load_settings()
    model_name = settings["ollama"]["memory"]["model"]

    prompt_path = ROOT_DIR / "prompts" / "memory_extractor.txt"
    system_prompt = prompt_path.read_text(encoding="utf-8")

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    payload = {
        "model": model_name,
        "messages": messages,
        "think": False,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0
        }
    }

    result = _send_request(payload)
    raw_content = _get_content(result)

    try:
        output = json.loads(raw_content)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Memory extractor returned invalid JSON: {raw_content}"
        ) from error

    if not isinstance(output, dict):
        raise RuntimeError("Invalid memory JSON structure!")

    memories = output.get("memories")

    if not isinstance(memories, list):
        raise RuntimeError("Invalid memories format!")

    valid_subjects = {
        "user",
        "stheno",
        "other",
        "unknown"
    }

    valid_categories = {
        "fact",
        "preference",
        "goal",
        "project",
        "event",
        "general"
    }

    validated_memories = []

    for index, memory in enumerate(memories):

        if not isinstance(memory, dict):
            raise RuntimeError(
                f"Memory at index {index} must be a dictionary!"
            )

        subject = memory.get("subject")
        category = memory.get("category")
        content = memory.get("content")
        importance = memory.get("importance")

        # Validate subject
        if not isinstance(subject, str):
            raise RuntimeError(
                f"Invalid subject at memory index {index}!"
            )

        subject = subject.strip().lower()

        if subject not in valid_subjects:
            raise RuntimeError(
                f"Unknown subject at memory index {index}: {subject}"
            )

        # Validate category
        if not isinstance(category, str):
            raise RuntimeError(
                f"Invalid category at memory index {index}!"
            )

        category = category.strip().lower()

        if category not in valid_categories:
            raise RuntimeError(
                f"Unknown category at memory index {index}: {category}"
            )

        # Validate content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                f"Invalid content at memory index {index}!"
            )

        # Validate importance
        if type(importance) is not int or not 1 <= importance <= 5:
            raise RuntimeError(
                f"Invalid importance at memory index {index}!"
            )

        validated_memories.append({
            "subject": subject,
            "category": category,
            "content": content.strip(),
            "importance": importance
        })

    return {
        "memories": validated_memories
    }



# AI Reranker
# Chỉ trả về ID của những memory thực sự liên quan.
def select_relevant_memory_ids(
    user_message: str,
    candidates: list[dict],
    history: list[dict] | None = None,
    max_results: int = 5
) -> list[int]:

    if not isinstance(user_message, str) or not user_message.strip():
        return []

    if not candidates:
        return []

    settings = load_settings()
    model_name = settings["ollama"]["memory"]["model"]

    prompt_path = ROOT_DIR / "prompts" / "memory_retriever.txt"

    with open(prompt_path, "r", encoding="utf-8") as file:
        system_prompt = file.read()

    # Chỉ lấy lịch sử gần nhất làm ngữ cảnh.
    # Không biến lịch sử thành các câu hỏi truy xuất độc lập.
    history_data = []

    for message in (history or [])[-10:]:
        role = message.get("role")
        content = message.get("content")

        if role not in ("user", "assistant"):
            continue

        if not isinstance(content, str) or not content.strip():
            continue

        history_data.append({
            "role": role,
            "content": content.strip()
        })

    # Subject đã được xử lý ở SubjectResolver và MemoryRetriever.
    # Reranker chỉ cần đánh giá mức độ liên quan của nội dung.
    memory_data = [
        {
            "id": memory["id"],
            "category": memory["category"],
            "content": memory["content"]
        }
        for memory in candidates
    ]

    user_data = {
        "user_message": user_message,
        "history": history_data,
        "max_results": max_results,
        "candidates": memory_data
    }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": json.dumps(
                    user_data,
                    ensure_ascii=False
                )
            }
        ],
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": 0
        }
    }

    result = _send_request(payload)
    content = _get_content(result)

    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Invalid JSON from memory reranker!")

    if not isinstance(data, dict):
        raise ValueError("Memory reranker must return a JSON object!")

    memory_ids = data.get("memory_ids")

    print("\n========== RERANKER DEBUG ==========")
    print("Selected IDs:", memory_ids)
    print("Candidate memories:")

    for memory in candidates:
        print(
            f"ID={memory['id']} | "
            f"Subject={memory.get('subject')} | "
            f"Content={memory['content']}"
        )

    print("====================================")

    if not isinstance(memory_ids, list):
        raise ValueError("Invalid memory_ids format!")

    # Chỉ chấp nhận ID thực sự tồn tại trong candidates.
    allowed_ids = {
        memory["id"]
        for memory in candidates
    }

    selected_ids = []
    seen = set()

    for memory_id in memory_ids:

        if isinstance(memory_id, str) and memory_id.isdigit():
            memory_id = int(memory_id)

        if type(memory_id) is not int:
            continue

        if memory_id not in allowed_ids:
            continue

        if memory_id in seen:
            continue

        selected_ids.append(memory_id)
        seen.add(memory_id)

        if len(selected_ids) >= max_results:
            break

    return selected_ids


if __name__ == "__main__":
    print("===== STHENO BRAIN CHECK =====")

    if check_ollama():
        print("Brain status: READY")
    else:
        print("Brain status: NOT READY")