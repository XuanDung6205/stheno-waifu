# voice.initialize()	Kiểm tra engine và khởi tạo
# voice.speak(text)	Generate rồi phát audio
# voice.generate(text)	Chỉ tạo WAV, không phát
# voice.play(path)	Phát file WAV đã có
# voice.stop()	Ngắt playback hoặc inference
# voice.is_speaking	True/False, player đang chạy
# voice.is_generating	True/False, đang generate audio
# voice.set_speed(1.1)	Chỉnh tốc độ
# voice.set_voice(path, text)	Cài voice reference
# voice.set_instruct(text)	Cài hướng dẫn biểu cảm/giọng
# voice.shutdown()	Dừng và giải phóng process

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Optional
import sys
from .voice_config import GENERATION
# from .cached_infer import main as cached_infer


# =========================================================
# CONFIGURATION
# =========================================================
VOICE_DIR = Path(__file__).parent

OMNIVOICE_PYTHON = Path(
    r"D:\AI\Stheno\OmniVoice\.venv\Scripts\python.exe"
)

CACHED_INFER_SCRIPT = VOICE_DIR / "cached_infer.py"

VOICE_PROFILE = (
    VOICE_DIR / "voice_profiles" / "stheno_voice.pt"
)


OMNIVOICE_EXE = Path(
    r"D:\AI\Stheno\OmniVoice\.venv\Scripts\omnivoice-infer.exe"
)

OUTPUT_DIR = Path(
    r"D:\AI\Stheno\VoiceOutput"
)

VLC_PATHS = [
    Path(r"C:\Program Files\VideoLAN\VLC\vlc.exe"),
    Path(r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"),
]

# DEFAULT_LANGUAGE = "Vietnamese"
# DEFAULT_SPEED = 1.0


# =========================================================
# STHENO VOICE CONTROLLER
# =========================================================

class SthenoVoice:

    def __init__(self):
        self.speed = GENERATION.speed
        self.instruct = GENERATION.instruct
        self.duration = GENERATION.duration
        self.inference_steps = GENERATION.inference_steps
        self.denoise = GENERATION.denoise
        self.guidance_scale = GENERATION.guidance_scale
        self.preprocess_prompt = GENERATION.preprocess_prompt
        self.postprocess_output = GENERATION.postprocess_output
        self.language = GENERATION.default_language
        self.output_dir = OUTPUT_DIR

        # Process management
        self._player: Optional[subprocess.Popen] = None
        self._inference: Optional[subprocess.Popen] = None

        self._lock = threading.RLock()

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    # =====================================================
    # INITIALIZATION
    # =====================================================

    def initialize(self) -> bool:

        if not OMNIVOICE_PYTHON.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy OmniVoice Python:\n"
                f"{OMNIVOICE_PYTHON}"
            )

        if not CACHED_INFER_SCRIPT.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy cached inference script:\n"
                f"{CACHED_INFER_SCRIPT}"
            )

        if not VOICE_PROFILE.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy voice profile:\n"
                f"{VOICE_PROFILE}"
            )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        print("[SthenoVoice] Cached voice engine initialized.")
        print(f"[SthenoVoice] Python: {OMNIVOICE_PYTHON}")
        print(f"[SthenoVoice] Profile: {VOICE_PROFILE}")
        print(f"[SthenoVoice] Output: {self.output_dir}")

        return True

    # =====================================================
    # VLC
    # =====================================================

    def _find_vlc(self) -> Optional[str]:

        # Ưu tiên PATH
        vlc = shutil.which("vlc")

        if vlc:
            return vlc

        # Kiểm tra vị trí cài đặt phổ biến
        for path in VLC_PATHS:
            if path.is_file():
                return str(path)

        return None

    # =====================================================
    # STATUS
    # =====================================================

    @property
    def is_speaking(self) -> bool:

        with self._lock:

            if self._player is None:
                return False

            return self._player.poll() is None

    @property
    def is_generating(self) -> bool:

        with self._lock:

            if self._inference is None:
                return False

            return self._inference.poll() is None

    # =====================================================
    # VOICE SETTINGS
    # =====================================================

    def set_voice(
        self,
        ref_audio: Optional[str],
        ref_text: Optional[str] = None
    ):

        if ref_audio is not None:

            path = Path(ref_audio)

            if not path.is_file():
                raise FileNotFoundError(
                    f"Không tìm thấy voice reference:\n{path}"
                )

            self.ref_audio = str(path)

        else:
            self.ref_audio = None

        self.ref_text = ref_text

        print("[SthenoVoice] Voice reference updated.")

    def set_instruct(self, instruct: Optional[str]):

        self.instruct = instruct

        print("[SthenoVoice] Voice instruction updated.")

    def set_speed(self, speed: float):

        if speed <= 0:
            raise ValueError(
                "Speed phải lớn hơn 0."
            )

        self.speed = speed

        print(f"[SthenoVoice] Speed: {self.speed}")

    # =====================================================
    # TEXT TO SPEECH
    # =====================================================

    
    def generate(self, text: str) -> Path:

        text = text.strip()

        if not text:
            raise ValueError("Không thể tạo audio từ text rỗng.")

        if not OMNIVOICE_PYTHON.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy Python:\n{OMNIVOICE_PYTHON}"
            )

        if not CACHED_INFER_SCRIPT.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy cached_infer.py:\n{CACHED_INFER_SCRIPT}"
            )

        if not VOICE_PROFILE.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy voice profile:\n{VOICE_PROFILE}"
            )

        filename = (
            f"stheno_{time.strftime('%Y%m%d_%H%M%S')}_"
            f"{uuid.uuid4().hex[:8]}.wav"
        )

        output = self.output_dir / filename

        command = [
            str(OMNIVOICE_PYTHON),
            str(CACHED_INFER_SCRIPT),
            "--text", text,
            "--output", str(output),
            "--speed", str(self.speed),
        ]

        if self.instruct:
            command.extend([
                "--instruct", self.instruct
            ])

        print("[SthenoVoice] Generating with cached voice profile...")

        with self._lock:

            self._inference = subprocess.Popen(
                command,
                cwd=str(OMNIVOICE_PYTHON.parent.parent.parent),
            )

            process = self._inference

        return_code = process.wait()

        with self._lock:

            if self._inference is process:
                self._inference = None

        if return_code != 0:
            raise RuntimeError(
                f"Cached OmniVoice failed with exit code {return_code}"
            )

        if not output.is_file():
            raise RuntimeError(
                "OmniVoice không tạo được file WAV."
            )

        if output.stat().st_size == 0:
            raise RuntimeError("File WAV rỗng.")

        print(f"[SthenoVoice] Audio generated: {output}")

        return output


    # =====================================================
    # AUDIO PLAYBACK
    # =====================================================

    def play(
        self,
        audio_path: str | Path,
        wait: bool = False
    ):

        audio_path = Path(audio_path)

        if not audio_path.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy audio:\n{audio_path}"
            )

        # Không phát chồng audio
        self.stop()

        vlc = self._find_vlc()

        if not vlc:

            print(
                "[SthenoVoice] VLC không tồn tại. "
                "Fallback sang Windows default player."
            )

            os.startfile(str(audio_path))
            return

        command = [
            vlc,
            "--intf", "dummy",
            "--no-video",
            "--play-and-exit",
            str(audio_path),
        ]

        player = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        with self._lock:
            self._player = player

        print("[SthenoVoice] Playing audio.")

        if wait:
            player.wait()

            with self._lock:
                if self._player is player:
                    self._player = None

    # =====================================================
    # SPEAK
    # =====================================================

    # nhớ gọi hàm này vì nó vừa generate sau đó mới gọi tiếp speak luôn
    def speak(
        self,
        text: str,
        wait: bool = False
    ) -> Path:

        audio_path = self.generate(text)

        self.play(
            audio_path,
            wait=wait
        )

        return audio_path

    # =====================================================
    # STOP / INTERRUPT
    # =====================================================

    @staticmethod
    def _terminate_process(
        process: Optional[subprocess.Popen]
    ):

        if process is None:
            return

        if process.poll() is not None:
            return

        try:
            process.terminate()
            process.wait(timeout=2)

        except subprocess.TimeoutExpired:

            process.kill()

            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass

    def stop(self):

        with self._lock:

            player = self._player
            inference = self._inference

            self._player = None
            self._inference = None

        # Dừng player
        self._terminate_process(player)

        # Dừng inference nếu đang generate
        self._terminate_process(inference)

        print("[SthenoVoice] Playback / generation stopped.")

    # =====================================================
    # SHUTDOWN
    # =====================================================

    def shutdown(self):

        self.stop()

        print("[SthenoVoice] Voice engine shutdown.")
