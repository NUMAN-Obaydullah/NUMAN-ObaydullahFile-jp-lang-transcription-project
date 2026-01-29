"""Audio capture and device utilities."""
import numpy as np
import sounddevice as sd
from typing import Callable, Optional, Any


def list_input_devices() -> None:
    """List all available audio input devices."""
    devices = sd.query_devices()
    print("\nAvailable audio input devices:")
    print("-" * 70)
    for i, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            print(f"[{i}] {d['name']}")
            print(f"    Channels: {d['max_input_channels']}, Sample Rate: {d.get('default_samplerate')} Hz")
    print("-" * 70)


def create_audio_stream(
    device: Optional[int],
    samplerate: int,
    channels: int,
    blocksize: int,
    callback: Callable[[np.ndarray, int, Any, Any], None]
) -> sd.InputStream:
    """
    Create and return configured audio stream.
    
    Args:
        device: Audio device index (None for system default)
        samplerate: Sample rate in Hz
        channels: Number of audio channels
        blocksize: Block size in frames
        callback: Callback function for audio data
    
    Returns:
        Configured audio input stream
    """
    return sd.InputStream(
        samplerate=samplerate,
        channels=channels,
        dtype="float32",
        blocksize=blocksize,
        device=device,
        callback=callback,
    )


def calculate_audio_level(audio_data: np.ndarray) -> float:
    """
    Calculate RMS audio level for visualization.
    
    Args:
        audio_data: Audio data as numpy array
    
    Returns:
        RMS level as float between 0 and 1
    """
    if audio_data.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(audio_data ** 2)))
