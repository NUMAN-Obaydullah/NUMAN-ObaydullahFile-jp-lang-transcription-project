# Quick Start Guide

This guide will help you get the real-time transcription system up and running in under 10 minutes.

## Prerequisites Check

Before starting, ensure you have:
- ✅ macOS with Apple Silicon (M1/M2/M3)
- ✅ Python 3.9 or higher
- ✅ Microphone connected
- ✅ Terminal access

## Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `mlx-whisper` - Whisper model for Apple Silicon
- `numpy` - Numerical computing
- `sounddevice` - Audio capture
- `aiohttp` - Web server and WebSocket
- `aiohttp-cors` - CORS support
- `requests` - HTTP client for LLM API

**Expected time**: 2-3 minutes

## Step 2: Setup LLM Server (Optional)

The system works without LLM predictions, but for full functionality:

### Option A: Use llama-server

```bash
# Download LFM2.5-1.2B-JP GGUF model
# (Visit Hugging Face or model repository for download link)

# Start llama-server
llama-server \
  --model path/to/lfm2.5-1.2b-jp.gguf \
  --port 8080 \
  --ctx-size 4096 \
  --n-gpu-layers 35
```

### Option B: Skip LLM Setup

The system will automatically disable semantic predictions if LLM server is not available. You'll still get real-time transcription.

**Expected time**: 5 minutes (if using LLM)

## Step 3: Verify Setup

Run the validation script:

```bash
python validate_setup.py
```

You should see:
- ✅ File Structure PASSED
- ✅ Python Imports PASSED (if dependencies installed)
- ✅ Lib Modules PASSED
- ✅ Audio Devices PASSED

If any test fails, install missing dependencies or check error messages.

**Expected time**: 30 seconds

## Step 4: List Audio Devices

Find your microphone:

```bash
python streaming_server.py --list-devices
```

Output will show available devices:
```
Available audio input devices:
----------------------------------------------------------------------
[0] MacBook Pro Microphone
    Channels: 1, Sample Rate: 48000.0 Hz
[1] External USB Microphone
    Channels: 2, Sample Rate: 44100.0 Hz
----------------------------------------------------------------------
```

Note the device number you want to use (usually 0 for built-in mic).

**Expected time**: 10 seconds

## Step 5: Start the Server

### Basic Start (Default Settings)

```bash
python streaming_server.py
```

### Custom Start (With Options)

```bash
python streaming_server.py \
  --device 0 \
  --port 8000 \
  --whisper-model mlx-community/whisper-large-v3-turbo
```

You should see:
```
======================================================================
Real-time Audio Transcription & Semantic Prediction Server
======================================================================
Server: http://localhost:8000
Whisper model: mlx-community/whisper-large-v3-turbo
LLM: http://127.0.0.1:8080/v1/chat/completions (model: lfm2.5-jp)
Audio: device=0, sr=16000Hz
Window: 8.0s, Step: 2.0s, Language: ja
======================================================================
Starting server...
Server started at http://localhost:8000
Open your browser and navigate to the URL above
Press Ctrl+C to stop
```

**Expected time**: 5-10 seconds (first run may take longer as Whisper model loads)

## Step 6: Open Web Interface

1. Open your web browser
2. Navigate to: `http://localhost:8000`
3. You should see the web interface with:
   - Timeline panel (left)
   - Predictions panel (right)
   - Control buttons (bottom)

## Step 7: Start Transcribing

1. Click **"Start Recording"** button
2. Speak into your microphone in Japanese (or configured language)
3. Watch transcript appear in real-time
4. See predictions update automatically (if LLM enabled)

## Step 8: Test Export

1. After some transcription, click **"Export TXT"** or **"Export JSON"**
2. File will download automatically
3. Open the file to verify transcript

## Troubleshooting Quick Fixes

### Issue: Server won't start

**Fix**: Check if port 8000 is already in use
```bash
python streaming_server.py --port 8080
```

### Issue: No transcription appearing

**Fix**: 
1. Check microphone permissions in System Preferences
2. Try different device: `--device 1`
3. Speak louder and clearer

### Issue: LLM predictions not showing

**Fix**: This is normal if llama-server is not running. Transcription will still work.

### Issue: Browser shows "Disconnected"

**Fix**: 
1. Refresh the page
2. Check server is still running in terminal
3. Check for firewall blocking localhost connections

## Common Configuration Examples

### Fast Mode (Lower Accuracy)
```bash
python streaming_server.py \
  --whisper-model mlx-community/whisper-large-v3-turbo \
  --window-s 6.0 \
  --step-s 1.5
```

### High Accuracy Mode
```bash
python streaming_server.py \
  --whisper-model mlx-community/whisper-large-v3-mlx \
  --window-s 10.0 \
  --step-s 2.5
```

### English Transcription
```bash
python streaming_server.py --lang en
```

### Custom Server Address (Access from other devices)
```bash
python streaming_server.py \
  --host 0.0.0.0 \
  --port 8000
```
Then access from other device: `http://YOUR_IP:8000`

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [web/README.md](web/README.md) for web interface details
- Explore command-line options: `python streaming_server.py --help`
- Try the standalone scripts:
  - `realtime_whisper_v3_to_txt.py` - CLI transcription only
  - `semantic_predict_from_transcription.py` - Batch predictions

## Getting Help

If you encounter issues:

1. Run validation: `python validate_setup.py`
2. Run logic tests: `python test_logic.py`
3. Check logs in terminal for error messages
4. Review troubleshooting section in README.md
5. Create an issue on GitHub with:
   - Error message
   - Output of `validate_setup.py`
   - Your configuration command

## Success Checklist

You've successfully set up the system when:
- [ ] Server starts without errors
- [ ] Web interface loads at http://localhost:8000
- [ ] "Start Recording" enables recording
- [ ] Transcript appears in timeline
- [ ] Export creates downloadable files
- [ ] Reset clears all data

## Performance Expectations

On a typical M1/M2 Mac:
- **Transcription lag**: 1-3 seconds behind real-time
- **LLM updates**: Every 3-6 seconds (configurable)
- **Memory usage**: 200-400MB
- **CPU usage**: 40-60% during active transcription

---

**Congratulations!** You now have a working real-time audio transcription system with semantic prediction capabilities.

For advanced usage and customization, see the full [README.md](README.md).
