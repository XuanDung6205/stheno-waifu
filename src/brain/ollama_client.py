import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError


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

def chat(message: str) -> str:
    """
    Send a message to Ollama and return AI response.
    """

    if not message.strip():
        raise ValueError("Message cannot be empty!")

    settings = load_settings()

    base_url = settings["ollama"]["base_url"].rstrip("/")
    model_name = settings["ollama"]["model"]

    url = f"{base_url}/api/chat" #endpoint để giao tiếp

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
        "stream": False
    }

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
    assistant_message = result.get(
        "message", {}
    ).get("content")

    if not assistant_message:
        raise RuntimeError(
            "Ollama returned an empty response!"
        )

    return assistant_message.strip()


if __name__ == "__main__":
    print("===== STHENO BRAIN CHECK =====")

    if check_ollama():
        print("Brain status: READY")
    else:
        print("Brain status: NOT READY")