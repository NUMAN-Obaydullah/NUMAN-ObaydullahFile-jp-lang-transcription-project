# Real-time Japanese Audio Transcription & Semantic Prediction System

A complete, integrated system for real-time audio transcription using Whisper Large V3 with semantic prediction powered by LFM2.5-1.2B-JP, featuring an interactive web interface for visualization and control.

## Features

- 🎤 **Real-time Audio Transcription**: Uses Whisper Large V3 (mlx-whisper) for accurate Japanese speech recognition
- 🧠 **Semantic Prediction**: LFM2.5-1.2B-JP model generates keywords, next terms, and running summaries
- 🌐 **Interactive Web Interface**: Modern, responsive web UI with timeline visualization
- 📊 **Live Updates**: WebSocket-based real-time updates with <100ms latency
- 💾 **Export Support**: Download transcripts in TXT or JSON format
- ⚡ **High Performance**: Optimized for efficiency with sliding window approach
- 🔄 **Auto-Reconnection**: Robust WebSocket handling with automatic reconnection

## Architecture

```
┌─────────────┐
│ Microphone  │
└──────┬──────┘
       │ Audio Stream
       ↓
┌─────────────────────┐
│ Whisper Processor   │
│ (Sliding Window)    │
└──────┬──────────────┘
       │ Text Segments
       ↓
┌─────────────────────┐
│ Semantic Predictor  │
│ (LFM2.5-1.2B-JP)    │
└──────┬──────────────┘
       │ Predictions
       ↓
┌─────────────────────┐
│ WebSocket Server    │
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐
│ Web Interface       │
│ (Timeline + UI)     │
└─────────────────────┘
```

## Prerequisites

- **Python**: 3.9 or higher
- **macOS**: With Apple Silicon (M1/M2/M3) for MLX support
- **LLM Server**: llama-server running with LFM2.5-1.2B-JP model
- **Microphone**: Audio input device
- **Browser**: Chrome, Firefox, or Safari (for web interface)

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd NUMAN-ObaydullahFile-jp-lang-transcription-project
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup LLM Server

Download and start the LFM2.5-1.2B-JP model with llama-server:

```bash
# Download LFM2.5-1.2B-JP GGUF model
# (Model download instructions depend on where you obtain it)

# Start llama-server
llama-server \
  --model path/to/lfm2.5-1.2b-jp.gguf \
  --port 8080 \
  --ctx-size 4096 \
  --n-gpu-layers 35
```

### 4. List Audio Devices (Optional)

To find your audio device index:

```bash
python streaming_server.py --list-devices
```

## Quick Start

### Basic Usage

Start the streaming server with default settings:

```bash
python streaming_server.py
```

Then open your browser and navigate to:
```
http://localhost:8000
```

### With Custom Configuration

```bash
python streaming_server.py \
  --host 0.0.0.0 \
  --port 8080 \
  --device 1 \
  --whisper-model mlx-community/whisper-large-v3-mlx \
  --update-every-lines 5
```

## Usage Guide

### Web Interface

1. **Start Recording**: Click "Start Recording" button to begin audio capture and transcription
2. **View Transcription**: Watch the timeline update in real-time with timestamped text segments
3. **Monitor Predictions**: Observe keywords, next terms, and summary updates in the right panel
4. **Stop Recording**: Click "Stop Recording" to pause (can resume later)
5. **Export**: Save transcript as TXT or JSON file
6. **Reset**: Clear all data and start fresh

### Timeline Features

- **Auto-scroll**: Automatically follows live transcription (can be disabled)
- **Timestamps**: Each segment shows start → end time
- **Hover Effects**: Interactive highlighting on hover
- **Color Coding**: New segments highlighted in green

### Predictions Panel

- **Keywords**: 5-12 important keywords from conversation context
- **Next Terms**: 5-12 predicted upcoming words/phrases
- **Summary**: 1-2 sentence summary of conversation so far
- **Performance Metrics**: TTFT, generation speed, and total time

## Configuration Options

### Server Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `localhost` | Server host address |
| `--port` | `8000` | Server port number |

### Audio Options

| Option | Default | Description |
|--------|---------|-------------|
| `--device` | `None` | Audio device index (None = system default) |
| `--sr` | `16000` | Sample rate in Hz |
| `--list-devices` | - | List available audio devices and exit |

### Whisper Options

| Option | Default | Description |
|--------|---------|-------------|
| `--whisper-model` | `mlx-community/whisper-large-v3-turbo` | Whisper model path or repo |
| `--window-s` | `8.0` | Transcription window in seconds |
| `--step-s` | `2.0` | Slide step in seconds |
| `--lang` | `ja` | Language code (ja, en, etc.) |

### LLM Options

| Option | Default | Description |
|--------|---------|-------------|
| `--llm-url` | `http://127.0.0.1:8080/v1/chat/completions` | LLM server URL |
| `--llm-model` | `lfm2.5-jp` | LLM model name |
| `--update-every-lines` | `3` | Update predictions every N lines |
| `--max-tokens` | `180` | Maximum tokens per LLM call |
| `--temperature` | `0.2` | LLM sampling temperature |

## Configuration Examples

### Fast Transcription (Lower Accuracy)

```bash
python streaming_server.py \
  --whisper-model mlx-community/whisper-large-v3-turbo \
  --window-s 6.0 \
  --step-s 1.5
```

### High Accuracy (Slower)

```bash
python streaming_server.py \
  --whisper-model mlx-community/whisper-large-v3-mlx \
  --window-s 10.0 \
  --step-s 2.5
```

### English Transcription

```bash
python streaming_server.py \
  --lang en \
  --llm-url http://localhost:8080/v1/chat/completions
```

### More Frequent LLM Updates

```bash
python streaming_server.py \
  --update-every-lines 2 \
  --max-tokens 200
```

## Troubleshooting

### LLM Connection Error

**Problem**: "Could not initialize semantic predictor"

**Solution**:
- Ensure llama-server is running on port 8080
- Check the `--llm-url` parameter
- System continues with transcription only (predictions disabled)

### Audio Device Not Found

**Problem**: "Error opening audio device"

**Solution**:
1. Run `python streaming_server.py --list-devices`
2. Note the device index you want to use
3. Run with `--device <index>` parameter

### No Transcription Output

**Problem**: Timeline remains empty

**Solution**:
- Check microphone permissions in system settings
- Verify audio levels (speak loudly and clearly)
- Try different `--device` index
- Check system microphone is not muted

### WebSocket Connection Failed

**Problem**: Web interface shows "Disconnected"

**Solution**:
- Refresh the browser page
- Check server is running (look for "Server started" message)
- Check firewall settings
- Try accessing via `http://127.0.0.1:8000`

### Poor Transcription Quality

**Problem**: Many incorrect words or missing text

**Solution**:
- Use better microphone (reduce background noise)
- Speak clearly and at moderate pace
- Increase `--window-s` for more context
- Switch to `whisper-large-v3-mlx` for better accuracy

## Performance Tips

### Optimize Speed

- Use `whisper-large-v3-turbo` model
- Reduce `--window-s` to 6-7 seconds
- Reduce `--update-every-lines` to 5+
- Lower `--max-tokens` to 120-150

### Optimize Accuracy

- Use `whisper-large-v3-mlx` model
- Increase `--window-s` to 9-10 seconds
- Increase `--step-s` for more overlap
- Use good quality microphone

### Reduce Memory Usage

- Use turbo model
- Lower `--max-tokens`
- Increase `--update-every-lines`

## File Structure

```
.
├── streaming_server.py          # Main integrated server
├── lib/
│   ├── __init__.py              # Library package init
│   ├── audio_utils.py           # Audio capture utilities
│   ├── whisper_processor.py     # Whisper transcription
│   └── semantic_predictor.py    # LLM predictions
├── web/
│   ├── index.html               # Web interface
│   ├── css/
│   │   └── style.css            # Styling
│   └── js/
│       ├── main.js              # Main app logic
│       ├── timeline.js          # Timeline visualization
│       └── export.js            # Export functionality
├── realtime_whisper_v3_to_txt.py           # Standalone transcription script
├── semantic_predict_from_transcription.py  # Standalone prediction script
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git exclusions
└── README.md                    # This file
```

## WebSocket API

### Server → Client Messages

#### Transcript Event
```json
{
  "type": "transcript",
  "data": {
    "start": 12.34,
    "end": 17.89,
    "text": "こんにちは",
    "timestamp": "2026-01-29T10:30:45"
  }
}
```

#### Prediction Event
```json
{
  "type": "prediction",
  "data": {
    "keywords": ["会議", "プロジェクト"],
    "next_terms": ["について", "進捗"],
    "summary": "プロジェクトの進捗について議論",
    "audio_time": 45.67,
    "metrics": {
      "ttft_ms": 125.5,
      "chars_per_sec": 45.2,
      "total_s": 0.98
    }
  }
}
```

#### Status Event
```json
{
  "type": "status",
  "data": {
    "recording": true,
    "connected": true,
    "audio_time": 120.5
  }
}
```

#### Error Event
```json
{
  "type": "error",
  "data": {
    "message": "Error description",
    "code": "ERROR_CODE"
  }
}
```

### Client → Server Commands

#### Start Recording
```json
{
  "type": "start_recording"
}
```

#### Stop Recording
```json
{
  "type": "stop_recording"
}
```

#### Reset
```json
{
  "type": "reset"
}
```

#### Export
```json
{
  "type": "export",
  "format": "txt"  // or "json"
}
```

## Existing Scripts

The repository includes two standalone scripts that remain available:

### `realtime_whisper_v3_to_txt.py`

Command-line real-time transcription to text file:

```bash
python realtime_whisper_v3_to_txt.py \
  --out transcription.txt \
  --model mlx-community/whisper-large-v3-turbo \
  --lang ja
```

### `semantic_predict_from_transcription.py`

Generate semantic predictions from existing transcript file:

```bash
python semantic_predict_from_transcription.py \
  --transcript transcription.txt \
  --out-events events.jsonl \
  --out-final final.json \
  --follow
```

## Development

### Adding New Features

The modular architecture makes it easy to extend:

- **Audio processing**: Modify `lib/audio_utils.py`
- **Transcription logic**: Modify `lib/whisper_processor.py`
- **LLM predictions**: Modify `lib/semantic_predictor.py`
- **Server behavior**: Modify `streaming_server.py`
- **Web UI**: Modify files in `web/` directory

### Testing

Test individual components:

```python
# Test audio devices
python -c "from lib.audio_utils import list_input_devices; list_input_devices()"

# Test Whisper processor
# (Create test script with sample audio)

# Test semantic predictor
# (Create test script with sample text)
```

## Performance Targets

The system is designed to meet these performance goals:

- **Transcription latency**: < 3 seconds behind real-time
- **LLM prediction latency**: < 500ms per update
- **WebSocket message delay**: < 50ms
- **UI update rate**: Smooth 60fps animations
- **Memory usage**: < 500MB for 1-hour session
- **CPU usage**: < 80% on M1/M2 Mac during active transcription

## Known Limitations

- **MLX Support**: Requires Apple Silicon (M1/M2/M3) Mac
- **Language Support**: Optimized for Japanese, but supports other languages
- **LLM Dependency**: Semantic predictions require external llama-server
- **Single User**: Designed for single-user local usage
- **Audio Format**: Currently supports microphone input only (not file input)

## Future Enhancements

Potential improvements for future versions:

- [ ] Support for audio file input (not just microphone)
- [ ] Multi-language UI translations
- [ ] Speaker diarization (identify different speakers)
- [ ] Custom vocabulary/terminology support
- [ ] Integration with other LLM backends (OpenAI, Anthropic, etc.)
- [ ] Mobile app version
- [ ] Recording/playback of audio alongside transcript
- [ ] Search functionality in transcript history
- [ ] Cloud deployment support

## License

MIT License - See repository for full license text

## Support

For issues, questions, or contributions:
- Check the Troubleshooting section above
- Review existing GitHub issues
- Create a new issue with detailed information

## Acknowledgments

- **Whisper**: OpenAI's Whisper model for speech recognition
- **MLX**: Apple's MLX framework for efficient ML on Apple Silicon
- **LFM2.5**: Language Foundation Model for Japanese
- **llama.cpp**: For LLM inference backend

---

**Note**: This system is designed for research and development purposes. For production use, consider additional testing, security hardening, and error handling.
