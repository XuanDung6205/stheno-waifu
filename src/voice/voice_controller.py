
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
import uuid
import json
import socket
import secrets

from pathlib import Path
from typing import Optional

from .voice_config import GENERATION


# =========================================================
# CONFIGURATION
# =========================================================

VOICE_DIR = Path(__file__).parent

OMNIVOICE_PYTHON = Path(
    r"D:\AI\Stheno\OmniVoice\.venv\Scripts\python.exe"
)

VOICE_WORKER_SCRIPT = VOICE_DIR / "voice_worker.py"

VOICE_PROFILE = VOICE_DIR / "voice_profiles" / "stheno_voice.pt"

OUTPUT_DIR = Path(r"D:\AI\Stheno\VoiceOutput")

VLC_PATHS = [
    Path(r"C:\Program Files\VideoLAN\VLC\vlc.exe"),
    Path(r"C:\Program Files (x86)\VideoLAN\vlc\vlc.exe"),
]


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
        self.ref_audio = None
        self.ref_text = None

        # Worker process
        self._worker: Optional[subprocess.Popen] = None

        # IPC - Socket
        self._server: Optional[socket.socket] = None
        self._connection: Optional[socket.socket] = None

        self._reader = None
        self._writer = None

        self._worker_token = None

        # Playback
        self._player: Optional[subprocess.Popen] = None

        # Status
        self._generating = False
        self._initialized = False
        self._active_request_id = None

        # Locks
        self._lock = threading.RLock()
        self._generation_lock = threading.Lock()

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    # =====================================================
    # SOCKET HELPERS
    # =====================================================

    @staticmethod
    def _send_message(writer, message: dict):

        writer.write(
            json.dumps(
                message,
                ensure_ascii=False,
            ) + "\n"
        )

        writer.flush()

    @staticmethod
    def _receive_message(reader):

        line = reader.readline()

        if not line:
            return None

        return json.loads(line)

    # =====================================================
    # INITIALIZATION
    # =====================================================

    def initialize(self) -> bool:

        if self._initialized:
            print("[SthenoVoice] Already initialized.")
            return True

        if not OMNIVOICE_PYTHON.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy OmniVoice Python:\n"
                f"{OMNIVOICE_PYTHON}"
            )

        if not VOICE_WORKER_SCRIPT.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy voice_worker.py:\n"
                f"{VOICE_WORKER_SCRIPT}"
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

        # -------------------------------------------------
        # Create Socket Server
        # -------------------------------------------------

        self._server = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        # Cho phép sử dụng lại socket sau khi shutdown
        self._server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        # Chỉ lắng nghe localhost
        self._server.bind(
            ("127.0.0.1", 0)
        )

        # Port 0: Windows tự chọn port trống
        host, port = self._server.getsockname()

        self._server.listen(1)

        self._server.settimeout(300)

        # Token xác thực Worker
        self._worker_token = secrets.token_hex(32)

        print(
            f"[SthenoVoice] Socket server listening "
            f"on {host}:{port}"
        )

        # -------------------------------------------------
        # Start Worker Process
        # -------------------------------------------------

        command = [
            str(OMNIVOICE_PYTHON),
            str(VOICE_WORKER_SCRIPT),
            "--host",
            host,
            "--port",
            str(port),
            "--token",
            self._worker_token,
        ]

        print("[SthenoVoice] Starting voice worker...")

        worker_env = os.environ.copy()

        worker_env["PYTORCH_CUDA_ALLOC_CONF"] = (
            "expandable_segments:True"
        )


        self._worker = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            env=worker_env,
        )

        print(
            f"[SthenoVoice] Worker PID: "
            f"{self._worker.pid}"
        )

        # -------------------------------------------------
        # Wait for Worker Connection
        # -------------------------------------------------

        try:

            print("[SthenoVoice] Waiting for Worker connection...")

            self._connection, address = self._server.accept()

            print(
                f"[SthenoVoice] Worker connected from {address}"
            )

            # Timeout cho quá trình startup
            self._connection.settimeout(300)

            self._reader = self._connection.makefile(
                "r",
                encoding="utf-8",
            )

            self._writer = self._connection.makefile(
                "w",
                encoding="utf-8",
            )

            # -------------------------------------------------
            # Handshake
            # -------------------------------------------------

            hello = self._receive_message(
                self._reader
            )

            if hello is None:
                raise RuntimeError(
                    "Worker đóng kết nối trước handshake."
                )

            if hello.get("type") != "hello":
                raise RuntimeError(
                    f"Handshake không hợp lệ: {hello}"
                )

            if hello.get("token") != self._worker_token:
                raise RuntimeError(
                    "Worker authentication failed."
                )

            print("[SthenoVoice] Worker authenticated.")

            # -------------------------------------------------
            # Wait READY
            # -------------------------------------------------

            print(
                "[SthenoVoice] Waiting for model loading..."
            )

            response = self._receive_message(
                self._reader
            )

            if response is None:
                raise RuntimeError(
                    "Worker đóng kết nối trong quá trình startup."
                )

            if response.get("type") == "startup_error":

                error = response.get(
                    "error",
                    "Unknown error",
                )

                traceback_text = response.get(
                    "traceback",
                    "",
                )

                raise RuntimeError(
                    f"Voice worker startup failed:\n"
                    f"{error}\n{traceback_text}"
                )

            if response.get("type") != "ready":

                raise RuntimeError(
                    f"Unexpected worker response: {response}"
                )

            if response.get("status") != "success":

                raise RuntimeError(
                    f"Worker failed to initialize: {response}"
                )

            # -------------------------------------------------
            # Startup completed
            # -------------------------------------------------

            # Không giới hạn thời gian generate
            self._connection.settimeout(None)

            self._initialized = True

            print("[SthenoVoice] Voice worker READY.")
            print(
                f"[SthenoVoice] Worker PID: "
                f"{self._worker.pid}"
            )
            print(
                f"[SthenoVoice] Output: "
                f"{self.output_dir}"
            )

            return True

        except Exception:

            self.shutdown()

            raise

        finally:

            # Server chỉ cần trong startup để Worker kết nối.
            if self._server is not None:

                try:
                    self._server.close()
                except OSError:
                    pass

                self._server = None

    # =====================================================
    # VLC
    # =====================================================

    def _find_vlc(self) -> Optional[str]:

        vlc = shutil.which("vlc")

        if vlc:
            return vlc

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
            return self._generating

    @property
    def is_worker_alive(self) -> bool:

        return (
            self._worker is not None
            and self._worker.poll() is None
        )

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

        if self._initialized:
            print(
                "[SthenoVoice] Warning: worker hiện đang giữ "
                "voice profile đã load lúc startup. "
                "Dynamic profile reload chưa được tích hợp."
            )

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
            raise ValueError(
                "Không thể tạo audio từ text rỗng."
            )

        if not self._initialized:
            raise RuntimeError(
                "Voice worker chưa được initialize."
            )

        if not self.is_worker_alive:
            raise RuntimeError(
                "Voice worker đã chết."
            )

        # Chỉ một request generate tại một thời điểm
        with self._generation_lock:

            request_id = uuid.uuid4().hex

            filename = (
                f"stheno_{time.strftime('%Y%m%d_%H%M%S')}_"
                f"{request_id[:8]}.wav"
            )

            output = self.output_dir / filename

            # -------------------------------------------------
            # Create Request
            # -------------------------------------------------

            request = {
                "type": "generate",
                "id": request_id,
                "text": text,
                "output": str(output),
                "speed": self.speed,
                "instruct": self.instruct,
            }

            print(
                f"[SthenoVoice] Sending request: "
                f"{request_id}"
            )

            with self._lock:

                self._generating = True
                self._active_request_id = request_id

            try:

                # -------------------------------------------------
                # Send Request
                # -------------------------------------------------

                self._send_message(
                    self._writer,
                    request,
                )

                # -------------------------------------------------
                # Wait Response
                # -------------------------------------------------

                response = self._receive_message(
                    self._reader
                )

                if response is None:

                    raise RuntimeError(
                        "Worker đóng kết nối trong khi generate."
                    )

                if not self.is_worker_alive:

                    raise RuntimeError(
                        "Voice worker died during generation."
                    )

                # -------------------------------------------------
                # Validate Request ID
                # -------------------------------------------------

                if (
                    response.get("type") != "generate_result"
                    or response.get("id") != request_id
                ):

                    raise RuntimeError(
                        f"Response không khớp request.\n"
                        f"Expected ID: {request_id}\n"
                        f"Received: {response}"
                    )

                # -------------------------------------------------
                # Check Result
                # -------------------------------------------------

                if response.get("status") != "success":

                    error = response.get(
                        "error",
                        "Unknown error",
                    )

                    traceback_text = response.get(
                        "traceback",
                        "",
                    )

                    raise RuntimeError(
                        f"Voice generation failed:\n"
                        f"{error}\n{traceback_text}"
                    )

                # -------------------------------------------------
                # Validate WAV
                # -------------------------------------------------

                if not output.is_file():

                    raise RuntimeError(
                        "Worker báo thành công nhưng "
                        "không tìm thấy WAV."
                    )

                if output.stat().st_size == 0:

                    raise RuntimeError(
                        "File WAV rỗng."
                    )

                print(
                    f"[SthenoVoice] Audio generated: {output}"
                )

                return output

            finally:

                with self._lock:

                    self._generating = False
                    self._active_request_id = None

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

        self.stop_playback()

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
    # PROCESS TERMINATION
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

    # =====================================================
    # STOP PLAYBACK
    # =====================================================

    def stop_playback(self):

        with self._lock:

            player = self._player
            self._player = None

        self._terminate_process(player)

    def stop(self):

        self.stop_playback()

        if self.is_generating:

            print(
                "[SthenoVoice] Generation is in progress. "
                "Worker hiện chưa hỗ trợ interrupt inference."
            )

        print("[SthenoVoice] Playback stopped.")

    # =====================================================
    # SHUTDOWN
    # =====================================================

    def shutdown(self):

        print("[SthenoVoice] Shutting down...")

        # -------------------------------------------------
        # Stop VLC
        # -------------------------------------------------

        self.stop_playback()

        # -------------------------------------------------
        # Request Worker Shutdown
        # -------------------------------------------------

        worker = self._worker

        if worker is not None and worker.poll() is None:

            try:

                if self._writer is not None:

                    self._send_message(
                        self._writer,
                        {
                            "type": "shutdown",
                        },
                    )

                # Đợi Worker ACK
                if self._reader is not None:

                    try:
                        if self._connection is not None:
                            self._connection.settimeout(5)

                        
                        response = self._receive_message(
                            self._reader
                        )

                        if response is not None:

                            print(
                                "[SthenoVoice] Shutdown response: "
                                f"{response}"
                            )

                    except (OSError, ValueError) as e:

                        print(
                            f"[SthenoVoice] Shutdown ACK error: {e}"
                        )

                # Worker giải phóng model
                worker.wait(timeout=30)

            except subprocess.TimeoutExpired:

                print(
                    "[SthenoVoice] Worker shutdown timeout. "
                    "Terminating..."
                )

                self._terminate_process(worker)

            except Exception as e:

                print(
                    f"[SthenoVoice] Shutdown error: {e}"
                )

                self._terminate_process(worker)

        # -------------------------------------------------
        # Cleanup Socket
        # -------------------------------------------------

        for stream in (
            self._reader,
            self._writer,
        ):

            if stream is not None:

                try:
                    stream.close()
                except OSError:
                    pass

        if self._connection is not None:

            try:
                self._connection.close()
            except OSError:
                pass

        if self._server is not None:

            try:
                self._server.close()
            except OSError:
                pass

        # -------------------------------------------------
        # Reset State
        # -------------------------------------------------

        self._worker = None

        self._server = None
        self._connection = None

        self._reader = None
        self._writer = None

        self._worker_token = None

        self._initialized = False
        self._generating = False
        self._active_request_id = None

        print("[SthenoVoice] Voice engine shutdown.")
