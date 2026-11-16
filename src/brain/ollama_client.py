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


def chat(message: str, history: list[dict] | None = None) -> str:
    """
    Send conversation history and get a normal text response.
    """

    if not message.strip():
        raise ValueError("Message cannot be empty!")

    settings = load_settings()

    model_name = settings["ollama"]["chat"]["model"]

    messages = list(history or [])

    messages.append({
        "role": "user",
        "content": message
    })

    # messages.insert(0, {
    #     "role": "system",
    #     "content": system_prompt
    # })

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

    if not user_message.strip():
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
        "stream": False
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

    # Validate each memory
    for index, memory in enumerate(memories):

        if not isinstance(memory, dict):
            raise RuntimeError(
                f"Memory at index {index} must be a dictionary!"
            )

        category = memory.get("category")
        content = memory.get("content")
        importance = memory.get("importance")

        if not isinstance(category, str) or not category.strip():
            raise RuntimeError(
                f"Invalid category at memory index {index}!"
            )

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                f"Invalid content at memory index {index}!"
            )

        # bool is a subclass of int in Python, so check exact type
        if type(importance) is not int or not 1 <= importance <= 5:
            raise RuntimeError(
                f"Invalid importance at memory index {index}!"
            )

    return {
        "memories": memories
    }

#AI Reranker
#Hàm này chỉ trả về ID của những ký ức mà AI lựa chọn.
def select_relevant_memory_ids(
    user_message: str,
    candidates: list[dict],
    max_results: int = 5
) -> list[int]:

    if not user_message.strip():
        return []

    if not candidates:
        return []

    settings = load_settings()

    model_name = settings["ollama"]["memory"]["model"]

    prompt_path = ROOT_DIR / "prompts" / "memory_retriever.txt"

    with open(prompt_path, "r", encoding="utf-8") as file:
        system_prompt = file.read()

    memory_data = [
        {
            "id": memory["id"],
            "category": memory["category"],
            "content": memory["content"],
            "importance": memory["importance"]
        }
        for memory in candidates
    ]

    user_data = {
        "user_message": user_message,
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

    data = json.loads(content)

    memory_ids = data.get("memory_ids")

    if not isinstance(memory_ids, list):
        raise ValueError("Invalid memory_ids format!")

    allowed_ids = {
        memory["id"] for memory in candidates
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

    return selected_ids[:max_results]


if __name__ == "__main__":
    print("===== STHENO BRAIN CHECK =====")

    if check_ollama():
        print("Brain status: READY")
    else:
        print("Brain status: NOT READY")