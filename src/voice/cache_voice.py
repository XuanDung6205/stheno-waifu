# # tạo voice mẫu từ folder voice_profiles và lưu vào stheno_voice.pt

# from pathlib import Path
# import torch

# from omnivoice import OmniVoice, VoiceClonePrompt

# # =========================
# # CONFIGURATION
# # =========================

# BASE_DIR = Path(__file__).parent

# REF_AUDIO = BASE_DIR / "voice_profiles" / "reference.wav"
# # REF_TEXT_FILE = BASE_DIR / "voice_profiles" / "reference.txt"

# PROFILE_DIR = BASE_DIR / "voice_profiles"
# PROFILE_PATH = PROFILE_DIR / "stheno_voice.pt"

# MODEL_NAME = "k2-fsa/OmniVoice"
# DEVICE = "cuda:0"


# # =========================
# # MAIN
# # =========================

# def main():
#     if not REF_AUDIO.exists():
#         print(f"[ERROR] Reference audio not found: {REF_AUDIO}")
#         return

#     # if not REF_TEXT_FILE.exists():
#     #     print(f"[ERROR] Reference text not found: {REF_TEXT_FILE}")
#     #     return

#     # ref_text = REF_TEXT_FILE.read_text(encoding="utf-8").strip()

#     # if not ref_text:
#     #     print("[ERROR] Reference text is empty!")
#     #     return

#     PROFILE_DIR.mkdir(parents=True, exist_ok=True)

#     print("[1/3] Loading OmniVoice model...")

#     model = OmniVoice.from_pretrained(
#         MODEL_NAME,
#         device_map=DEVICE,
#         dtype=torch.float16,
#     )

#     print("[2/3] Encoding reference voice...")

#     prompt = model.create_voice_clone_prompt(
#         ref_audio=str(REF_AUDIO),
#         # ref_text=ref_text,
#     )

#     print("[3/3] Saving voice profile...")

#     prompt.save(str(PROFILE_PATH))

#     print("\n" + "=" * 40)
#     print("VOICE PROFILE CREATED SUCCESSFULLY")
#     print(f"Saved to: {PROFILE_PATH}")
#     print("=" * 40)

#     del prompt
#     del model

#     if torch.cuda.is_available():
#         torch.cuda.empty_cache()


# if __name__ == "__main__":
#     main()