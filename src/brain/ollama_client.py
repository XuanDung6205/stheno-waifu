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


if __name__ == "__main__":
    print("===== STHENO BRAIN CHECK =====")

    if check_ollama():
        print("Brain status: READY")
    else:
        print("Brain status: NOT READY")