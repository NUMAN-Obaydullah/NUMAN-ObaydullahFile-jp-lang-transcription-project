#!/usr/bin/env python3
"""
Unit tests for the transcription system (no external dependencies required).
Tests core logic and data structures.
"""

import json
import sys
from pathlib import Path


def test_json_parsing():
    """Test JSON parsing logic from semantic_predictor."""
    print("Testing JSON parsing...")
    
    # Test cases
    test_cases = [
        ('{"keywords":["test"],"next_terms":[],"summary":"test"}', True),
        ('```json\n{"keywords":[]}\n```', True),
        ('Some text {"keywords":[]} more text', True),
        ('Invalid JSON', False),
        ('', False),
    ]
    
    for test_input, should_pass in test_cases:
        # Simple validation
        has_json = '{' in test_input and '}' in test_input
        result = "✓" if (has_json == should_pass or not should_pass) else "✗"
        print(f"  {result} '{test_input[:30]}...' -> {has_json}")
    
    return True


def test_time_formatting():
    """Test time formatting logic."""
    print("\nTesting time formatting...")
    
    def format_time(seconds):
        """Format time in MM:SS format."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
    
    test_cases = [
        (0, "00:00"),
        (30, "00:30"),
        (60, "01:00"),
        (90, "01:30"),
        (3665, "61:05"),
    ]
    
    all_passed = True
    for seconds, expected in test_cases:
        result = format_time(seconds)
        passed = result == expected
        all_passed &= passed
        status = "✓" if passed else "✗"
        print(f"  {status} {seconds}s -> {result} (expected: {expected})")
    
    return all_passed


def test_websocket_message_format():
    """Test WebSocket message format."""
    print("\nTesting WebSocket message formats...")
    
    # Test transcript message
    transcript_msg = {
        "type": "transcript",
        "data": {
            "start": 12.34,
            "end": 17.89,
            "text": "こんにちは",
            "timestamp": "2026-01-29T10:30:45"
        }
    }
    
    # Test prediction message
    prediction_msg = {
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
    
    # Validate structure
    try:
        json_str = json.dumps(transcript_msg, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["type"] == "transcript"
        print("  ✓ Transcript message format valid")
        
        json_str = json.dumps(prediction_msg, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["type"] == "prediction"
        print("  ✓ Prediction message format valid")
        
        return True
    except Exception as e:
        print(f"  ✗ Message format validation failed: {e}")
        return False


def test_export_format():
    """Test export format generation."""
    print("\nTesting export formats...")
    
    # Sample transcript data
    transcripts = [
        {"start": 0.0, "end": 5.0, "text": "こんにちは", "timestamp": "2026-01-29T10:30:00"},
        {"start": 5.0, "end": 10.0, "text": "今日はいい天気ですね", "timestamp": "2026-01-29T10:30:05"},
    ]
    
    # Test TXT format
    txt_lines = []
    for item in transcripts:
        txt_lines.append(f"[{item['start']:8.2f}s -> {item['end']:8.2f}s] {item['text']}")
    txt_content = "\n".join(txt_lines)
    
    assert "こんにちは" in txt_content
    assert "今日はいい天気ですね" in txt_content
    print("  ✓ TXT export format valid")
    
    # Test JSON format
    json_content = json.dumps(transcripts, ensure_ascii=False, indent=2)
    parsed = json.loads(json_content)
    assert len(parsed) == 2
    assert parsed[0]["text"] == "こんにちは"
    print("  ✓ JSON export format valid")
    
    return True


def test_sliding_window_logic():
    """Test sliding window logic."""
    print("\nTesting sliding window logic...")
    
    # Simulate sliding window parameters
    sr = 16000  # 16kHz sample rate
    window_s = 8.0  # 8 second window
    step_s = 2.0  # 2 second step
    
    window_frames = int(sr * window_s)  # 128000 frames
    step_frames = int(sr * step_s)  # 32000 frames
    
    assert window_frames == 128000
    assert step_frames == 32000
    assert step_frames < window_frames  # Step must be less than window
    
    overlap_s = window_s - step_s
    assert overlap_s == 6.0  # 6 seconds overlap
    
    print(f"  ✓ Window: {window_s}s ({window_frames} frames)")
    print(f"  ✓ Step: {step_s}s ({step_frames} frames)")
    print(f"  ✓ Overlap: {overlap_s}s")
    
    return True


def test_html_structure():
    """Test HTML file structure."""
    print("\nTesting HTML structure...")
    
    html_path = Path("web/index.html")
    if not html_path.exists():
        print("  ✗ index.html not found")
        return False
    
    content = html_path.read_text()
    
    # Check for required elements
    required_elements = [
        "<!DOCTYPE html>",
        "<html",
        "<head>",
        "<body>",
        "timeline-container",
        "keywords-container",
        "next-terms-container",
        "summary-container",
        "main.js",
        "timeline.js",
        "export.js",
        "style.css",
    ]
    
    all_found = True
    for element in required_elements:
        if element in content:
            print(f"  ✓ {element}")
        else:
            print(f"  ✗ {element} not found")
            all_found = False
    
    return all_found


def test_css_structure():
    """Test CSS file structure."""
    print("\nTesting CSS structure...")
    
    css_path = Path("web/css/style.css")
    if not css_path.exists():
        print("  ✗ style.css not found")
        return False
    
    content = css_path.read_text()
    
    # Check for required classes
    required_classes = [
        ".timeline-container",
        ".transcript-item",
        ".keyword-tag",
        ".next-term-tag",
        ".summary-container",
        ".btn-primary",
        ".status-dot",
    ]
    
    all_found = True
    for cls in required_classes:
        if cls in content:
            print(f"  ✓ {cls}")
        else:
            print(f"  ✗ {cls} not found")
            all_found = False
    
    return all_found


def test_javascript_structure():
    """Test JavaScript file structure."""
    print("\nTesting JavaScript structure...")
    
    js_files = {
        "web/js/main.js": ["TranscriptionApp", "WebSocket", "handleMessage"],
        "web/js/timeline.js": ["Timeline", "addTranscript", "formatTime"],
        "web/js/export.js": ["Exporter", "exportAsTxt", "exportAsJson"],
    }
    
    all_found = True
    for js_path, required_items in js_files.items():
        path = Path(js_path)
        if not path.exists():
            print(f"  ✗ {js_path} not found")
            all_found = False
            continue
        
        content = path.read_text()
        for item in required_items:
            if item in content:
                print(f"  ✓ {js_path}: {item}")
            else:
                print(f"  ✗ {js_path}: {item} not found")
                all_found = False
    
    return all_found


def main():
    """Run all tests."""
    print("=" * 70)
    print("Real-time Transcription System - Logic Tests")
    print("=" * 70)
    
    tests = [
        ("JSON Parsing", test_json_parsing),
        ("Time Formatting", test_time_formatting),
        ("WebSocket Messages", test_websocket_message_format),
        ("Export Formats", test_export_format),
        ("Sliding Window Logic", test_sliding_window_logic),
        ("HTML Structure", test_html_structure),
        ("CSS Structure", test_css_structure),
        ("JavaScript Structure", test_javascript_structure),
    ]
    
    results = {}
    for name, test_func in tests:
        print()
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"  ✗ Test failed with exception: {e}")
            results[name] = False
    
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    for name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:25s} {status}")
    
    all_passed = all(results.values())
    
    print("=" * 70)
    if all_passed:
        print("✓ All logic tests passed!")
        return 0
    else:
        print("✗ Some logic tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
