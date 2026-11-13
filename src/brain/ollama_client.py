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
    model_name = settings["ollama"]["model"]

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

    if model_name not in models:
        print(f"[ERROR] Model not found: {model_name}")
        print("Available models:")

        for model in models:
            print(f" - {model}")

        return False

    print(f"[OK] Model found: {model_name}")

    return True

def chat(message: str, history: list[dict] | None = None) -> dict:
    """
    Send a message to Ollama and return AI response.
    """

    if not message.strip():
        raise ValueError("Message cannot be empty!")

    settings = load_settings()

    base_url = settings["ollama"]["base_url"].rstrip("/")
    model_name = settings["ollama"]["model"]

    url = f"{base_url}/api/chat" #endpoint để giao tiếp

    # Copy previous conversation history
    messages = list(history or [])

    # Add current user message
    messages.append({
        "role": "user",
        "content": message
    })

    prompt_path = ROOT_DIR / "prompts" / "chat_system.txt"
    system_prompt = prompt_path.read_text(encoding="utf-8")

    # Add system prompt to the beginning
    messages.insert(0, {
        "role": "system",
        "content": system_prompt
    })

    #gửi cho AI
    payload = {
        "model": model_name,
        "messages": messages,
        "think": False,
        "format": "json",
        "stream": False
    }

    # print("\n========== REQUEST DEBUG ==========")
    # print(json.dumps(
    #     payload["messages"],
    #     ensure_ascii=False,
    #     indent=2
    # ))
    # print("===================================\n")

    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )

    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

    except HTTPError as error:
        details = error.read().decode(
            "utf-8", errors="replace"
        )

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

    # {
    # "model": "stheno-waifu:latest",
    # "message": {
    #     "role": "assistant",
    #     "content": "Chào anh! Em vẫn đang đợi anh đây..."
    # },
    # "done": true
    # }

    #nhận kết quả
    assistant_message = result.get(
        "message", {}
    ).get("content")

    # chuyển assistant_message thành json
    try:
        output = json.loads(assistant_message)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Stheno returned invalid JSON!"
        ) from error

    # Kiểm tra Ollama có trả về content không
    if not isinstance(assistant_message, str) or not assistant_message.strip():

        print("\n========== RAW OLLAMA RESPONSE ==========")
        print(json.dumps(
            result,
            ensure_ascii=False,
            indent=4
        ))
        print("=========================================")

        raise RuntimeError(
            "Ollama returned an empty response!"
        )

    # Parse JSON
    try:
        output = json.loads(assistant_message)

    except json.JSONDecodeError as error:

        print("\n========== INVALID JSON ==========")
        print(assistant_message)
        print("==================================")

        raise RuntimeError(
            "Stheno returned invalid JSON!"
        ) from error

    # Kiểm tra JSON structure
    if not isinstance(output, dict):
        raise RuntimeError("Invalid JSON structure!")

    response_content = output.get("content")
    memories = output.get("memories")

    # Debug nếu thiếu content
    if not isinstance(response_content, str) or not response_content.strip():

        print("\n========== INVALID STHENO OUTPUT ==========")
        print(json.dumps(
            output,
            ensure_ascii=False,
            indent=4
        ))
        print("===========================================")

        raise RuntimeError(
            "Stheno returned an empty content field!"
        )

    if not isinstance(memories, list):
        raise RuntimeError("Invalid memories format!")

    # print("\n========== STHENO METRICS ==========")
    # print("Done reason:", result.get("done_reason"))
    # print("Prompt tokens:", result.get("prompt_eval_count"))
    # print("Generated tokens:", result.get("eval_count"))
    # print("Thinking chars:", len(result.get("thinking") or ""))
    # print("Content chars:", len(result.get("content") or ""))
    # print("====================================\n")

    # print("\n========== OLLAMA DEBUG ==========")
    # print(json.dumps(result, indent=2, ensure_ascii=False))
    # print("==================================\n")

    prompt_tokens = result.get("prompt_eval_count", 0)
    cached_tokens = result.get("prompt_eval_cached_count", 0)
    generated_tokens = result.get("eval_count", 0)

    total_tokens = prompt_tokens + generated_tokens

    print("\n========== STHENO TOKEN USAGE ==========")
    print(f"Input tokens:     {prompt_tokens}")
    print(f"Cached tokens:    {cached_tokens}")
    print(f"Output tokens:    {generated_tokens}")
    print(f"Total tokens:     {total_tokens}")
    print("========================================")

    if not assistant_message:
        
        # print("\n========== OLLAMA DEBUG ==========")
        # print(json.dumps(result, indent=2, ensure_ascii=False))
        # print("==================================\n")

        raise RuntimeError(
            "Ollama returned an empty response!"
        )

    return {
        "content": response_content.strip(),
        "memories": memories
    }


if __name__ == "__main__":
    print("===== STHENO BRAIN CHECK =====")

    if check_ollama():
        print("Brain status: READY")
    else:
        print("Brain status: NOT READY")