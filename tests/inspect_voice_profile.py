
from pathlib import Path
import torch
from omnivoice import VoiceClonePrompt

PROFILE_PATH = (
    Path(__file__).parent.parent
    / "src"
    / "voice"
    / "voice_profiles"
    / "stheno_voice.pt"
)

def describe(name, value):
    print(f"\n--- {name} ---")
    print("Type:", type(value).__name__)

    if isinstance(value, torch.Tensor):
        print("Shape:", tuple(value.shape))
        print("Dtype:", value.dtype)
        print("Device:", value.device)
        print("Num elements:", value.numel())
        print("Size:", f"{value.numel() * value.element_size():,} bytes")

    elif isinstance(value, (str, int, float, bool, type(None))):
        print("Value:", value)

    elif isinstance(value, dict):
        print("Keys:", list(value.keys()))

    elif isinstance(value, (list, tuple)):
        print("Length:", len(value))

    else:
        print("Value:", repr(value)[:200])


def main():
    if not PROFILE_PATH.exists():
        print("Profile not found:", PROFILE_PATH)
        return

    print("Profile file:", PROFILE_PATH)
    print("File size:", f"{PROFILE_PATH.stat().st_size / 1024:.2f} KB")

    print("\nLoading profile on CPU...")
    prompt = VoiceClonePrompt.load(str(PROFILE_PATH), map_location="cpu")

    print("\nProfile loaded successfully!")
    print("Class:", type(prompt))

    # Inspect attributes without printing raw tensor contents
    attributes = vars(prompt)

    print("\nAttributes:", list(attributes.keys()))

    for name, value in attributes.items():
        describe(name, value)

    print("\nInspection completed!")


if __name__ == "__main__":
    main()
