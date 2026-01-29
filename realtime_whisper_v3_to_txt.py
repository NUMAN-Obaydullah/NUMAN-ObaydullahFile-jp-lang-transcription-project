import argparse
import queue
import threading
import time
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd

# Fast path: feed waveform directly (no ffmpeg)
import mlx_whisper

# Optional: preload model once (reduces repeated load overhead)
def preload_model(path_or_repo: str):
    try:
        from mlx_whisper.transcribe import ModelHolder
        import mlx.core as mx
        ModelHolder.get_model(path_or_repo, mx.float16)
        return True
    except Exception:
        return False


def list_input_devices():
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            print(f"[{i}] {d['name']} (inputs={d['max_input_channels']}, default_sr={d.get('default_samplerate')})")


def transcribe_waveform(audio_f32_1d: np.ndarray,
                        model: str,
                        language: str,
                        prompt: str,
                        condition_on_previous_text: bool):
    """
    audio_f32_1d: float32 waveform in [-1, 1], 1D
    Returns: segments list (each has start/end/text)
    """
    # mlx_whisper.transcribe accepts waveform directly. :contentReference[oaicite:1]{index=1}
    result = mlx_whisper.transcribe(
        audio_f32_1d,
        path_or_hf_repo=model,
        language=language,
        initial_prompt=prompt if prompt else None,
        # For streaming chunks, turning this off often reduces repetitions.
        condition_on_previous_text=condition_on_previous_text,
        # Keep this False for speed + to avoid known memory growth issues in some versions.
        word_timestamps=False,
        verbose=False,
    )
    return result.get("segments", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-devices", action="store_true")
    ap.add_argument("--device", type=int, default=None)
    ap.add_argument("--sr", type=int, default=16000)
    ap.add_argument("--block-s", type=float, default=0.5, help="Audio callback block size in seconds")
    ap.add_argument("--window-s", type=float, default=8.0, help="Transcription window length (seconds)")
    ap.add_argument("--step-s", type=float, default=2.0, help="Slide step (seconds). Overlap = window - step")
    ap.add_argument("--model", type=str, default="mlx-community/whisper-large-v3-turbo",
                    help="Use v3 turbo for speed; or whisper-large-v3-mlx for max accuracy.")
    ap.add_argument("--lang", type=str, default="ja")
    ap.add_argument("--out", type=str, default=None,
                    help="Output text file (append). If omitted, a timestamped file is created.")
    ap.add_argument("--max-prompt-chars", type=int, default=300, help="How much previous text to feed as prompt")
    ap.add_argument("--condition-on-prev", action="store_true",
                    help="Enable condition_on_previous_text (can increase repetition in streaming).")
    args = ap.parse_args()

    # Auto-generate output filename if not provided
    if not args.out:
        args.out = f"transcription_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        print(f"Auto-generated output file: {args.out}")

    if args.list_devices:
        list_input_devices()
        return

    sr = args.sr
    block_frames = int(sr * args.block_s)
    window_frames = int(sr * args.window_s)
    step_frames = int(sr * args.step_s)

    if step_frames <= 0 or window_frames <= 0 or step_frames >= window_frames:
        raise ValueError("Require 0 < step_s < window_s")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Preload model (optional)
    preloaded = preload_model(args.model)
    print(f"Model: {args.model} (preloaded={preloaded})")
    print(f"Device={args.device} SR={sr} block={args.block_s}s window={args.window_s}s step={args.step_s}s")
    print(f"Writing to: {out_path.resolve()}")
    print("Listening… Ctrl+C to stop.\n")

    audio_q: "queue.Queue[np.ndarray]" = queue.Queue()

    def audio_callback(indata, frames, t, status):
        if status:
            print(status)
        # indata is float32 if dtype='float32'
        audio_q.put(indata.copy())

    # Sliding buffer + time bookkeeping
    buf = deque()  # holds np arrays shape (frames, 1)
    buf_len = 0
    buf_start_time = 0.0      # absolute audio-time for the first sample currently in buf
    committed_until = 0.0     # absolute audio-time that we already wrote up to
    prompt_text = ""          # rolling context prompt (last N chars)

    with sd.InputStream(
        samplerate=sr,
        channels=1,
        dtype="float32",
        blocksize=block_frames,
        device=args.device,
        callback=audio_callback,
    ):
        # Write header
        with out_path.open("a", encoding="utf-8") as f:
            f.write(f"--- START {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f.flush()

        try:
            while True:
                block = audio_q.get()
                buf.append(block)
                buf_len += len(block)

                # Wait until we have at least one full window
                if buf_len < window_frames:
                    continue

                # Build window waveform
                # (concatenate once per decode)
                window = np.concatenate(list(buf), axis=0)
                window = window[:window_frames, 0].astype(np.float32)  # 1D float32

                # Transcribe window
                segments = transcribe_waveform(
                    window,
                    model=args.model,
                    language=args.lang,
                    prompt=prompt_text[-args.max_prompt_chars:] if prompt_text else "",
                    condition_on_previous_text=args.condition_on_prev,
                )

                # Commit only stable region: [window_start, window_start + window_s - step_s]
                stable_end = buf_start_time + (args.window_s - args.step_s)

                new_lines = []
                new_texts = []

                for s in segments:
                    # s is typically dict-like: {'start':..., 'end':..., 'text':...}
                    s_start = float(s.get("start", 0.0)) + buf_start_time
                    s_end = float(s.get("end", 0.0)) + buf_start_time
                    text = (s.get("text") or "").strip()

                    if not text:
                        continue

                    # only write segments that end within stable region
                    if s_end > stable_end:
                        continue

                    # avoid duplicates: write only if beyond what we already committed
                    if s_end <= committed_until + 1e-3:
                        continue

                    new_lines.append(f"[{s_start:8.2f}s -> {s_end:8.2f}s] {text}")
                    new_texts.append(text)

                    committed_until = max(committed_until, s_end)

                if new_lines:
                    with out_path.open("a", encoding="utf-8") as f:
                        for line in new_lines:
                            print(line)
                            f.write(line + "\n")
                        f.flush()

                    # Notify user that committed chunk(s) finished only when idle
                    # i.e., buffer too small for another window and no queued blocks
                    try:
                        queue_empty = audio_q.empty()
                    except Exception:
                        queue_empty = True

                    if buf_len < window_frames and queue_empty:
                        print("transcription finished. waiting for new audio or quit for ctrl+c")

                    # Update rolling prompt with committed text
                    prompt_text = (prompt_text + " " + " ".join(new_texts)).strip()

                # Slide buffer by step
                # Drop step_frames from the left
                to_drop = step_frames
                while to_drop > 0 and buf:
                    left = buf[0]
                    if len(left) <= to_drop:
                        buf.popleft()
                        buf_len -= len(left)
                        to_drop -= len(left)
                    else:
                        buf[0] = left[to_drop:]
                        buf_len -= to_drop
                        to_drop = 0

                buf_start_time += args.step_s

        except KeyboardInterrupt:
            with out_path.open("a", encoding="utf-8") as f:
                f.write(f"--- STOP  {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.flush()
            print("\nStopped.")


if __name__ == "__main__":
    main()
