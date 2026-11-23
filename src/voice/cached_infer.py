
from pathlib import Path
import argparse

import torch
import soundfile as sf

from omnivoice import OmniVoice, VoiceClonePrompt
from voice_config import CONFIG


# =========================================================
# INFERENCE
# =========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)

    parser.add_argument(
        "--speed",
        type=float,
        default=CONFIG.speed,
    )

    parser.add_argument(
        "--instruct",
        default=CONFIG.instruct,
    )

    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------
    # Validate voice profile
    # -----------------------------------------------------

    if not CONFIG.voice_profile.is_file():
        raise FileNotFoundError(
            f"Voice profile not found: {CONFIG.voice_profile}"
        )

    # -----------------------------------------------------
    # Load model
    # -----------------------------------------------------

    print("[CachedInfer] Loading OmniVoice model...")

    model = OmniVoice.from_pretrained(
        CONFIG.model_name,
        device_map=CONFIG.device,
        dtype=torch.float16,
    )

    # -----------------------------------------------------
    # Load cached voice profile
    # -----------------------------------------------------

    print("[CachedInfer] Loading cached voice profile...")

    prompt = VoiceClonePrompt.load(
        str(CONFIG.voice_profile),
        map_location="cpu",
    )

    # -----------------------------------------------------
    # Generate
    # -----------------------------------------------------

    print("[CachedInfer] Generating...")

    audio = model.generate(
        text=args.text,
        language="Vietnamese",
        voice_clone_prompt=prompt,
        speed=args.speed,
        instruct=args.instruct,
    )

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    print("[CachedInfer] Saving audio...")

    sf.write(
        str(output_path),
        audio[0],
        model.sampling_rate,
    )

    print(f"[CachedInfer] Done: {output_path}")


if __name__ == "__main__":
    main()
