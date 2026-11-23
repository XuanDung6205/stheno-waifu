
from dataclasses import dataclass
from pathlib import Path


# =========================================================
# PATHS
# =========================================================

VOICE_DIR = Path(__file__).parent
PROJECT_ROOT = VOICE_DIR.parent.parent

OMNIVOICE_ROOT = Path(r"D:\AI\Stheno\OmniVoice")

OMNIVOICE_PYTHON = (
    OMNIVOICE_ROOT / ".venv" / "Scripts" / "python.exe"
)

CACHED_INFER_SCRIPT = VOICE_DIR / "cached_infer.py"

VOICE_PROFILE = (
    VOICE_DIR / "voice_profiles" / "stheno_voice.pt"
)

OUTPUT_DIR = Path(r"D:\AI\Stheno\VoiceOutput")


# =========================================================
# VOICE GENERATION SETTINGS
# =========================================================

@dataclass
class VoiceGenerationConfig:
    speed: float = 1.0
    duration: float | None = None

    inference_steps: int = 32
    denoise: bool = True
    guidance_scale: float = 2.0

    preprocess_prompt: bool = True
    postprocess_output: bool = True
    default_language = "Vietnamese"

    instruct: str = (
        "female, young adult, high pitch"
    )


# =========================================================
# PLAYBACK SETTINGS
# =========================================================

@dataclass
class VoicePlaybackConfig:
    vlc_path: Path | None = None
    volume: int = 100


@dataclass
class VoiceConfig:
    # Paths
    voice_dir: Path = Path(__file__).parent
    omnivoice_root: Path = Path(r"D:\AI\Stheno\OmniVoice")
    output_dir: Path = Path(r"D:\AI\Stheno\VoiceOutput")

    # Model
    model_name: str = "k2-fsa/OmniVoice"
    device: str = "cuda:0"

    # Generation
    speed: float = 1.0
    duration: float | None = None
    inference_steps: int = 32
    denoise: bool = True
    guidance_scale: float = 2.0
    preprocess_prompt: bool = True
    postprocess_output: bool = True
    instruct: str = "female, young adult, high pitch"

    @property
    def omnivoice_python(self):
        return self.omnivoice_root / ".venv" / "Scripts" / "python.exe"

    @property
    def cached_infer_script(self):
        return self.voice_dir / "cached_infer.py"

    @property
    def voice_profile(self):
        return self.voice_dir / "voice_profiles" / "stheno_voice.pt"




# =========================================================
# GLOBAL CONFIG INSTANCES
# =========================================================

GENERATION = VoiceGenerationConfig()
PLAYBACK = VoicePlaybackConfig()
CONFIG = VoiceConfig()