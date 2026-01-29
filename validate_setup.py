#!/usr/bin/env python3
"""
Validation script to check system setup without running the full server.
Tests that all modules can be imported and basic functionality works.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import numpy
        print("✓ numpy")
    except ImportError as e:
        print(f"✗ numpy: {e}")
        return False
    
    try:
        import sounddevice
        print("✓ sounddevice")
    except ImportError as e:
        print(f"✗ sounddevice: {e}")
        return False
    
    try:
        import requests
        print("✓ requests")
    except ImportError as e:
        print(f"✗ requests: {e}")
        return False
    
    try:
        import aiohttp
        print("✓ aiohttp")
    except ImportError as e:
        print(f"✗ aiohttp: {e}")
        return False
    
    try:
        import aiohttp_cors
        print("✓ aiohttp_cors")
    except ImportError as e:
        print(f"✗ aiohttp_cors: {e}")
        return False
    
    try:
        import mlx_whisper
        print("✓ mlx_whisper")
    except ImportError as e:
        print(f"✗ mlx_whisper: {e}")
        print("  Note: mlx_whisper requires Apple Silicon Mac")
        return False
    
    return True


def test_lib_modules():
    """Test that lib modules can be imported."""
    print("\nTesting lib modules...")
    
    try:
        from lib import audio_utils
        print("✓ lib.audio_utils")
    except ImportError as e:
        print(f"✗ lib.audio_utils: {e}")
        return False
    
    try:
        from lib import whisper_processor
        print("✓ lib.whisper_processor")
    except ImportError as e:
        print(f"✗ lib.whisper_processor: {e}")
        return False
    
    try:
        from lib import semantic_predictor
        print("✓ lib.semantic_predictor")
    except ImportError as e:
        print(f"✗ lib.semantic_predictor: {e}")
        return False
    
    return True


def test_file_structure():
    """Test that all required files exist."""
    print("\nTesting file structure...")
    
    required_files = [
        "streaming_server.py",
        "lib/__init__.py",
        "lib/audio_utils.py",
        "lib/whisper_processor.py",
        "lib/semantic_predictor.py",
        "web/index.html",
        "web/css/style.css",
        "web/js/main.js",
        "web/js/timeline.js",
        "web/js/export.js",
        "README.md",
        "requirements.txt",
        ".gitignore",
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} (missing)")
            all_exist = False
    
    return all_exist


def test_audio_devices():
    """Test that audio devices can be listed."""
    print("\nTesting audio device detection...")
    
    try:
        from lib.audio_utils import list_input_devices
        print("Attempting to list audio devices...")
        list_input_devices()
        print("✓ Audio device detection works")
        return True
    except Exception as e:
        print(f"✗ Audio device detection failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("=" * 70)
    print("Real-time Transcription System - Validation Script")
    print("=" * 70)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Imports", test_imports),
        ("Lib Modules", test_lib_modules),
        ("Audio Devices", test_audio_devices),
    ]
    
    results = {}
    for name, test_func in tests:
        print()
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"✗ {name} test failed with exception: {e}")
            results[name] = False
    
    print("\n" + "=" * 70)
    print("Validation Summary")
    print("=" * 70)
    
    for name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:20s} {status}")
    
    all_passed = all(results.values())
    
    print("=" * 70)
    if all_passed:
        print("✓ All validation tests passed!")
        print("\nYou can now run the server with:")
        print("  python streaming_server.py")
        return 0
    else:
        print("✗ Some validation tests failed.")
        print("\nPlease install missing dependencies:")
        print("  pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
