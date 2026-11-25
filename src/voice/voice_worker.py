
# Load OmniVoice một lần duy nhất.
# Load voice profile một lần.
# Chờ request từ controller qua Socket.
# Nhận text -> sinh WAV -> trả kết quả -> quay về chờ request tiếp.

# Process riêng chạy OmniVoice, giữ model trên VRAM.

from pathlib import Path
import argparse
import json
import socket
import traceback
import time
import gc

import torch
import soundfile as sf

from omnivoice import OmniVoice, VoiceClonePrompt
from voice_config import CONFIG


# =========================================================
# SOCKET HELPERS
# =========================================================

def send_message(writer, message: dict):
    """
    Gửi một message JSON qua Socket.
    Mỗi message kết thúc bằng newline (\n).
    """

    writer.write(json.dumps(message, ensure_ascii=False) + "\n")
    writer.flush()


def receive_message(reader):
    """
    Đọc một message JSON.
    Mỗi message tương ứng một dòng.
    """

    line = reader.readline()

    # Controller đóng kết nối
    if not line:
        return None

    return json.loads(line)

# =========================================================
# CUDA MEMORY HELPERS
# =========================================================

def log_cuda_memory(stage: str):
    if not torch.cuda.is_available():
        return

    device = CONFIG.device

    allocated = torch.cuda.memory_allocated(device) / 1024**3
    reserved = torch.cuda.memory_reserved(device) / 1024**3
    peak = torch.cuda.max_memory_allocated(device) / 1024**3

    print(
        f"[VoiceWorker][VRAM] {stage} "
        f"allocated={allocated:.2f}GB "
        f"reserved={reserved:.2f}GB "
        f"peak={peak:.2f}GB",
        flush=True,
    )


def cleanup_inference_memory():
    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# =========================================================
# WORKER
# =========================================================

def voice_worker_main(host: str, port: int, token: str):

    print("[VoiceWorker] Starting...", flush=True)

    connection = None
    reader = None
    writer = None

    model = None
    prompt = None

    try:

        # -------------------------------------------------
        # Connect to Controller
        # -------------------------------------------------

        print(
            f"[VoiceWorker] Connecting to Controller "
            f"{host}:{port}...",
            flush=True,
        )

        connection = socket.create_connection(
            (host, port),
            timeout=15,
        )

        # Sau khi connect thành công, bỏ timeout.
        # Generate có thể mất nhiều thời gian.
        connection.settimeout(None)

        reader = connection.makefile(
            "r",
            encoding="utf-8",
        )

        writer = connection.makefile(
            "w",
            encoding="utf-8",
        )

        # -------------------------------------------------
        # Handshake
        # -------------------------------------------------

        send_message(writer, {
            "type": "hello",
            "token": token,
        })

        print("[VoiceWorker] Connected to Controller.", flush=True)

        # -------------------------------------------------
        # Load model ONCE
        # -------------------------------------------------

        print("[VoiceWorker] Loading OmniVoice model...", flush=True)

        model = OmniVoice.from_pretrained(
            CONFIG.model_name,
            device_map=CONFIG.device,
            dtype=torch.float16,
        )

        # -------------------------------------------------
        # Load voice profile ONCE
        # -------------------------------------------------

        print("[VoiceWorker] Loading voice profile...", flush=True)

        prompt = VoiceClonePrompt.load(
            str(CONFIG.voice_profile),
            map_location="cpu",
        )


        # debug ---------------------------------------
        print("=" * 40)
        print("CUDA AVAILABLE:", torch.cuda.is_available())
        print("CONFIG DEVICE:", CONFIG.device)

        if torch.cuda.is_available():
            print("GPU:", torch.cuda.get_device_name(0))
            print(
                "VRAM Allocated:",
                round(torch.cuda.memory_allocated() / 1024**3, 2),
                "GB"
            )
            print(
                "VRAM Reserved:",
                round(torch.cuda.memory_reserved() / 1024**3, 2),
                "GB"
            )

        print("=" * 40, flush=True)
        # debug ---------------------------------------

        # -------------------------------------------------
        # READY
        # -------------------------------------------------

        print("[VoiceWorker] READY", flush=True)

        send_message(writer, {
            "type": "ready",
            "status": "success",
        })

    except Exception as e:

        print("[VoiceWorker] Startup error!", flush=True)
        traceback.print_exc()

        # Nếu đã kết nối được Controller,
        # gửi thông báo lỗi startup.
        if writer is not None:

            try:
                send_message(writer, {
                    "type": "startup_error",
                    "status": "error",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                })

            except Exception:
                pass

        return

    # =====================================================
    # REQUEST LOOP
    # =====================================================

    try:

        while True:

            # -------------------------------------------------
            # Wait for request
            # -------------------------------------------------

            request = receive_message(reader)

            # Controller đóng kết nối
            if request is None:

                print(
                    "[VoiceWorker] Controller disconnected.",
                    flush=True,
                )

                break

            request_type = request.get("type")

            # -------------------------------------------------
            # Shutdown
            # -------------------------------------------------

            if request_type == "shutdown":

                print(
                    "[VoiceWorker] Shutdown requested.",
                    flush=True,
                )

                send_message(writer, {
                    "type": "shutdown_result",
                    "status": "success",
                })

                break

            # -------------------------------------------------
            # Unknown request
            # -------------------------------------------------

            if request_type != "generate":

                print(
                    f"[VoiceWorker] Unknown request: "
                    f"{request_type}",
                    flush=True,
                )

                send_message(writer, {
                    "type": "error",
                    "id": request.get("id"),
                    "status": "error",
                    "error": f"Unknown request type: {request_type}",
                })

                continue

            # -------------------------------------------------
            # Generate
            # -------------------------------------------------

            request_id = request.get("id")

            text = request.get("text", "")
            output_path = Path(request["output"])
            speed = request.get("speed", CONFIG.speed)
            request_started = time.perf_counter()
            use_cuda = (
                torch.cuda.is_available()
                and str(CONFIG.device).startswith("cuda")
            )
            # instruct = request.get("instruct", CONFIG.instruct)

            try:

                print(
                    f"[VoiceWorker] Generating: {request_id} "
                    f"(text_chars={len(text)}, speed={speed}, "
                    f"device={CONFIG.device})",
                    flush=True,
                )

                mkdir_started = time.perf_counter()
                output_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                print(
                    f"[VoiceWorker][Timing] request={request_id} "
                    f"stage=prepare_output "
                    f"elapsed_s={time.perf_counter() - mkdir_started:.3f}",
                    flush=True,
                )

                # -------------------------------------------------
                # Inference
                # -------------------------------------------------

                if use_cuda:
                    cuda_memory_before = torch.cuda.memory_allocated(
                        CONFIG.device
                    ) / 1024**3
                    torch.cuda.synchronize(CONFIG.device)

                audio = None
                waveform = None

                if use_cuda:
                    torch.cuda.reset_peak_memory_stats(CONFIG.device)

                inference_started = time.perf_counter()
                try:
                    with torch.inference_mode():
                        audio = model.generate(
                            text=text,
                            language="Vietnamese",
                            voice_clone_prompt=prompt,
                            speed=speed,
                            # instruct=instruct,
                        )
                    if use_cuda:
                        torch.cuda.synchronize(CONFIG.device)
                finally:
                    inference_elapsed = time.perf_counter() - inference_started
                    inference_log = (
                        f"[VoiceWorker][Timing] request={request_id} "
                        f"stage=model.generate elapsed_s={inference_elapsed:.3f}"
                    )

                    if use_cuda:
                        cuda_memory_after = (
                            torch.cuda.memory_allocated(CONFIG.device) / 1024**3
                        )

                        inference_log += (
                            f" vram_allocated_after_gb={cuda_memory_after:.2f}"
                        )

                    print(inference_log, flush=True)
                    log_cuda_memory("after_generate")

                waveform = audio[0]
                sample_rate = model.sampling_rate
                audio_frames = len(waveform)
                audio_duration = audio_frames / sample_rate
                realtime_factor = (
                    inference_elapsed / audio_duration
                    if audio_duration > 0
                    else None
                )
                realtime_factor_text = (
                    f"{realtime_factor:.3f}"
                    if realtime_factor is not None
                    else "n/a"
                )
                print(
                    f"[VoiceWorker][Audio] request={request_id} "
                    f"shape={getattr(waveform, 'shape', 'unknown')} "
                    f"dtype={getattr(waveform, 'dtype', 'unknown')} "
                    f"sample_rate={sample_rate} frames={audio_frames} "
                    f"duration_s={audio_duration:.3f} "
                    f"generation_rtf={realtime_factor_text}",
                    flush=True,
                )

                # -------------------------------------------------
                # Save WAV
                # -------------------------------------------------

                save_started = time.perf_counter()
                sf.write(
                    str(output_path),
                    waveform,
                    sample_rate,
                )
                print(
                    f"[VoiceWorker][Timing] request={request_id} "
                    f"stage=save_wav "
                    f"elapsed_s={time.perf_counter() - save_started:.3f} "
                    f"file_bytes={output_path.stat().st_size}",
                    flush=True,
                )

                # -------------------------------------------------
                # Return result
                # -------------------------------------------------

                response_started = time.perf_counter()
                send_message(writer, {
                    "type": "generate_result",
                    "id": request_id,
                    "status": "success",
                    "path": str(output_path),
                })
                response_elapsed = time.perf_counter() - response_started

                print(
                    f"[VoiceWorker][Timing] request={request_id} "
                    f"stage=send_result elapsed_s={response_elapsed:.3f} "
                    f"total_elapsed_s={time.perf_counter() - request_started:.3f}",
                    flush=True,
                )
                print(
                    f"[VoiceWorker] Done: {request_id}",
                    flush=True,
                )

            except Exception as e:

                error_traceback = traceback.format_exc()
                print(
                    f"[VoiceWorker][Timing] request={request_id} "
                    f"stage=failed "
                    f"total_elapsed_s={time.perf_counter() - request_started:.3f}",
                    flush=True,
                )

                send_message(writer, {
                    "type": "generate_result",
                    "id": request_id,
                    "status": "error",
                    "error": str(e),
                    "traceback": error_traceback,
                })

                print(
                    f"[VoiceWorker] Error: {request_id}",
                    flush=True,
                )

                traceback.print_exc()
            finally:

                # Giải phóng audio tensor sau mỗi request
                waveform = None
                audio = None

                cleanup_inference_memory()

                log_cuda_memory("after_cleanup")

    except Exception:

        print(
            "[VoiceWorker] Communication error!",
            flush=True,
        )

        traceback.print_exc()

    # =====================================================
    # CLEANUP
    # =====================================================

    finally:

        print("[VoiceWorker] Releasing model...", flush=True)

        del prompt
        del model

        if torch.cuda.is_available():

            torch.cuda.empty_cache()

        # -------------------------------------------------
        # Close Socket
        # -------------------------------------------------

        if reader is not None:
            reader.close()

        if writer is not None:
            writer.close()

        if connection is not None:
            connection.close()

        print("[VoiceWorker] Exited.", flush=True)


# =========================================================
# ENTRY POINT
# =========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host",
        required=True,
    )

    parser.add_argument(
        "--port",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--token",
        required=True,
    )

    args = parser.parse_args()

    voice_worker_main(
        host=args.host,
        port=args.port,
        token=args.token,
    )


if __name__ == "__main__":
    main()
