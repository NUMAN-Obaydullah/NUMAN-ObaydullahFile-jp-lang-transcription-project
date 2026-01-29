"""Real-time Whisper transcription processor with sliding window."""
import logging
from collections import deque
from typing import List, Dict, Optional
import numpy as np
import mlx_whisper

logger = logging.getLogger(__name__)


class WhisperProcessor:
    """
    Real-time Whisper transcription with sliding window approach.
    
    Maintains an audio buffer and transcribes using overlapping windows
    to ensure accurate continuous transcription.
    """
    
    def __init__(
        self,
        model: str,
        sr: int,
        window_s: float,
        step_s: float,
        language: str = "ja",
        max_prompt_chars: int = 300,
        condition_on_previous_text: bool = False
    ):
        """
        Initialize Whisper processor.
        
        Args:
            model: Whisper model path or HuggingFace repo
            sr: Sample rate in Hz
            window_s: Transcription window length in seconds
            step_s: Slide step in seconds (overlap = window_s - step_s)
            language: Language code (default: ja)
            max_prompt_chars: Maximum characters for context prompt
            condition_on_previous_text: Enable conditioning on previous text
        """
        self.model = model
        self.sr = sr
        self.window_frames = int(sr * window_s)
        self.step_frames = int(sr * step_s)
        self.window_s = window_s
        self.step_s = step_s
        self.language = language
        self.max_prompt_chars = max_prompt_chars
        self.condition_on_previous_text = condition_on_previous_text
        
        # Sliding buffer
        self.buf: deque = deque()
        self.buf_len = 0
        self.buf_start_time = 0.0
        self.committed_until = 0.0
        self.prompt_text = ""
        
        logger.info(f"WhisperProcessor initialized: model={model}, sr={sr}, "
                   f"window={window_s}s, step={step_s}s, lang={language}")
    
    def add_audio_block(self, audio_data: np.ndarray) -> List[Dict]:
        """
        Add audio block to buffer and transcribe when window is full.
        
        Args:
            audio_data: Audio block as numpy array (frames, channels)
        
        Returns:
            List of new transcript segments with start/end/text
        """
        self.buf.append(audio_data)
        self.buf_len += len(audio_data)
        
        # Wait until we have at least one full window
        if self.buf_len < self.window_frames:
            return []
        
        # Build window waveform
        window = np.concatenate(list(self.buf), axis=0)
        window = window[:self.window_frames, 0].astype(np.float32)  # 1D float32
        
        # Transcribe window
        try:
            result = mlx_whisper.transcribe(
                window,
                path_or_hf_repo=self.model,
                language=self.language,
                initial_prompt=self.prompt_text[-self.max_prompt_chars:] if self.prompt_text else None,
                condition_on_previous_text=self.condition_on_previous_text,
                word_timestamps=False,
                verbose=False,
            )
            segments = result.get("segments", [])
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            segments = []
        
        # Commit only stable region: [window_start, window_start + window_s - step_s]
        stable_end = self.buf_start_time + (self.window_s - self.step_s)
        
        new_segments = []
        new_texts = []
        
        for s in segments:
            s_start = float(s.get("start", 0.0)) + self.buf_start_time
            s_end = float(s.get("end", 0.0)) + self.buf_start_time
            text = (s.get("text") or "").strip()
            
            if not text:
                continue
            
            # Only write segments that end within stable region
            if s_end > stable_end:
                continue
            
            # Avoid duplicates: write only if beyond what we already committed
            if s_end <= self.committed_until + 1e-3:
                continue
            
            new_segments.append({
                "start": s_start,
                "end": s_end,
                "text": text
            })
            new_texts.append(text)
            
            self.committed_until = max(self.committed_until, s_end)
        
        # Update rolling prompt with committed text
        if new_texts:
            self.prompt_text = (self.prompt_text + " " + " ".join(new_texts)).strip()
        
        # Slide buffer by step
        to_drop = self.step_frames
        while to_drop > 0 and self.buf:
            left = self.buf[0]
            if len(left) <= to_drop:
                self.buf.popleft()
                self.buf_len -= len(left)
                to_drop -= len(left)
            else:
                self.buf[0] = left[to_drop:]
                self.buf_len -= to_drop
                to_drop = 0
        
        self.buf_start_time += self.step_s
        
        return new_segments
    
    def get_buffer_time(self) -> float:
        """Return current audio time in seconds."""
        return self.buf_start_time + (self.buf_len / self.sr)
    
    def reset(self) -> None:
        """Clear all buffers."""
        self.buf.clear()
        self.buf_len = 0
        self.buf_start_time = 0.0
        self.committed_until = 0.0
        self.prompt_text = ""
        logger.info("WhisperProcessor reset")
