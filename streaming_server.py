#!/usr/bin/env python3
"""
Real-time Audio Transcription & Semantic Prediction Streaming Server

Integrates Whisper Large V3 transcription with LFM2.5-1.2B-JP semantic prediction,
serving real-time results via WebSocket to a web interface.
"""

import argparse
import asyncio
import json
import logging
import queue
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
import numpy as np

from aiohttp import web
import aiohttp_cors

from lib.audio_utils import list_input_devices, create_audio_stream, calculate_audio_level
from lib.whisper_processor import WhisperProcessor
from lib.semantic_predictor import SemanticPredictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StreamingServer:
    """
    Unified streaming server integrating:
    - Audio capture
    - Whisper transcription
    - LLM semantic prediction
    - WebSocket communication
    - Web interface serving
    """
    
    def __init__(self, args):
        self.args = args
        self.audio_q: queue.Queue = queue.Queue()
        self.websockets: Set[web.WebSocketResponse] = set()
        
        # Initialize processors
        self.whisper_processor: Optional[WhisperProcessor] = None
        self.semantic_predictor: Optional[SemanticPredictor] = None
        self.audio_stream = None
        
        # State
        self.is_recording = False
        self.audio_thread: Optional[threading.Thread] = None
        self.processing_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Transcript history
        self.transcript_history: List[Dict] = []
        
        logger.info("StreamingServer initialized")
    
    def audio_callback(self, indata, frames, t, status):
        """Audio callback for sounddevice stream."""
        if status:
            logger.warning(f"Audio status: {status}")
        if self.is_recording:
            self.audio_q.put(indata.copy())
    
    def start_recording(self):
        """Start audio recording and processing."""
        if self.is_recording:
            logger.warning("Already recording")
            return
        
        logger.info("Starting recording...")
        self.is_recording = True
        self.stop_event.clear()
        
        # Initialize Whisper processor
        try:
            logger.info("Preloading Whisper model...")
            from mlx_whisper.transcribe import ModelHolder
            import mlx.core as mx
            ModelHolder.get_model(self.args.whisper_model, mx.float16)
            logger.info("Whisper model preloaded")
        except Exception as e:
            logger.warning(f"Could not preload Whisper model: {e}")
        
        self.whisper_processor = WhisperProcessor(
            model=self.args.whisper_model,
            sr=self.args.sr,
            window_s=self.args.window_s,
            step_s=self.args.step_s,
            language=self.args.lang
        )
        
        # Initialize semantic predictor (if LLM available)
        try:
            self.semantic_predictor = SemanticPredictor(
                llm_url=self.args.llm_url,
                llm_model=self.args.llm_model,
                max_tokens=self.args.max_tokens,
                temperature=self.args.temperature,
                update_every_lines=self.args.update_every_lines
            )
            logger.info("Semantic predictor initialized")
        except Exception as e:
            logger.warning(f"Could not initialize semantic predictor: {e}")
            self.semantic_predictor = None
        
        # Start audio stream
        block_frames = int(self.args.sr * 0.5)  # 0.5s blocks
        self.audio_stream = create_audio_stream(
            device=self.args.device,
            samplerate=self.args.sr,
            channels=1,
            blocksize=block_frames,
            callback=self.audio_callback
        )
        self.audio_stream.start()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        # Broadcast status
        asyncio.run_coroutine_threadsafe(
            self._broadcast({
                "type": "status",
                "data": {
                    "recording": True,
                    "connected": True,
                    "audio_time": 0.0
                }
            }),
            asyncio.get_event_loop()
        )
        
        logger.info("Recording started")
    
    def stop_recording(self):
        """Stop audio recording and processing."""
        if not self.is_recording:
            logger.warning("Not recording")
            return
        
        logger.info("Stopping recording...")
        self.is_recording = False
        self.stop_event.set()
        
        # Stop audio stream
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None
        
        # Wait for processing thread
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
            self.processing_thread = None
        
        # Broadcast status
        asyncio.run_coroutine_threadsafe(
            self._broadcast({
                "type": "status",
                "data": {
                    "recording": False,
                    "connected": True,
                    "audio_time": self.whisper_processor.get_buffer_time() if self.whisper_processor else 0.0
                }
            }),
            asyncio.get_event_loop()
        )
        
        logger.info("Recording stopped")
    
    def reset(self):
        """Reset all state."""
        logger.info("Resetting state...")
        
        # Stop recording if active
        if self.is_recording:
            self.stop_recording()
        
        # Clear transcript history
        self.transcript_history = []
        
        # Reset processors
        if self.whisper_processor:
            self.whisper_processor.reset()
        if self.semantic_predictor:
            self.semantic_predictor.reset()
        
        # Broadcast reset
        asyncio.run_coroutine_threadsafe(
            self._broadcast({
                "type": "reset",
                "data": {}
            }),
            asyncio.get_event_loop()
        )
        
        logger.info("State reset complete")
    
    def _processing_loop(self):
        """Main processing loop (runs in separate thread)."""
        logger.info("Processing loop started")
        
        while not self.stop_event.is_set():
            try:
                # Get audio block (with timeout)
                try:
                    block = self.audio_q.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Process with Whisper
                segments = self.whisper_processor.add_audio_block(block)
                
                # Broadcast new segments
                for seg in segments:
                    # Add to history
                    transcript_item = {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"],
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                    }
                    self.transcript_history.append(transcript_item)
                    
                    # Broadcast transcript
                    asyncio.run_coroutine_threadsafe(
                        self._broadcast({
                            "type": "transcript",
                            "data": transcript_item
                        }),
                        asyncio.get_event_loop()
                    )
                    
                    # Add to semantic predictor
                    if self.semantic_predictor:
                        line = f"[{seg['start']:8.2f}s -> {seg['end']:8.2f}s] {seg['text']}"
                        try:
                            prediction = self.semantic_predictor.add_transcript_line(line)
                            if prediction:
                                # Broadcast prediction
                                asyncio.run_coroutine_threadsafe(
                                    self._broadcast({
                                        "type": "prediction",
                                        "data": {
                                            "keywords": prediction["keywords"],
                                            "next_terms": prediction["next_terms"],
                                            "summary": prediction["summary"],
                                            "audio_time": self.whisper_processor.get_buffer_time(),
                                            "metrics": prediction["metrics"]
                                        }
                                    }),
                                    asyncio.get_event_loop()
                                )
                        except Exception as e:
                            logger.error(f"Semantic prediction error: {e}")
                
                # Update status periodically
                if len(segments) > 0:
                    asyncio.run_coroutine_threadsafe(
                        self._broadcast({
                            "type": "status",
                            "data": {
                                "recording": True,
                                "connected": True,
                                "audio_time": self.whisper_processor.get_buffer_time()
                            }
                        }),
                        asyncio.get_event_loop()
                    )
            
            except Exception as e:
                logger.error(f"Processing loop error: {e}", exc_info=True)
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": "error",
                        "data": {
                            "message": str(e),
                            "code": "PROCESSING_ERROR"
                        }
                    }),
                    asyncio.get_event_loop()
                )
        
        logger.info("Processing loop stopped")
    
    async def _broadcast(self, message: Dict):
        """Broadcast message to all connected WebSocket clients."""
        if not self.websockets:
            return
        
        msg_json = json.dumps(message, ensure_ascii=False)
        
        # Send to all clients
        dead_sockets = set()
        for ws in self.websockets:
            try:
                await ws.send_str(msg_json)
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")
                dead_sockets.add(ws)
        
        # Remove dead sockets
        self.websockets -= dead_sockets
    
    async def websocket_handler(self, request):
        """WebSocket connection handler."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        logger.info(f"WebSocket connected. Total connections: {len(self.websockets)}")
        
        try:
            # Send initial state
            await ws.send_str(json.dumps({
                "type": "status",
                "data": {
                    "recording": self.is_recording,
                    "connected": True,
                    "audio_time": self.whisper_processor.get_buffer_time() if self.whisper_processor else 0.0
                }
            }, ensure_ascii=False))
            
            # Send transcript history
            for item in self.transcript_history:
                await ws.send_str(json.dumps({
                    "type": "transcript",
                    "data": item
                }, ensure_ascii=False))
            
            # Handle incoming messages
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        msg_type = data.get("type")
                        
                        if msg_type == "start_recording":
                            threading.Thread(target=self.start_recording, daemon=True).start()
                        elif msg_type == "stop_recording":
                            threading.Thread(target=self.stop_recording, daemon=True).start()
                        elif msg_type == "reset":
                            threading.Thread(target=self.reset, daemon=True).start()
                        elif msg_type == "export":
                            export_format = data.get("format", "txt")
                            export_data = self._generate_export(export_format)
                            await ws.send_str(json.dumps({
                                "type": "export_data",
                                "data": {
                                    "format": export_format,
                                    "content": export_data
                                }
                            }, ensure_ascii=False))
                        else:
                            logger.warning(f"Unknown message type: {msg_type}")
                    
                    except Exception as e:
                        logger.error(f"WebSocket message handling error: {e}")
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "data": {
                                "message": str(e),
                                "code": "MESSAGE_ERROR"
                            }
                        }, ensure_ascii=False))
                
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        
        finally:
            self.websockets.discard(ws)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.websockets)}")
        
        return ws
    
    def _generate_export(self, format: str) -> str:
        """Generate export data in specified format."""
        if format == "json":
            return json.dumps(self.transcript_history, ensure_ascii=False, indent=2)
        else:  # txt
            lines = []
            lines.append(f"--- Transcript Export {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            for item in self.transcript_history:
                lines.append(f"[{item['start']:8.2f}s -> {item['end']:8.2f}s] {item['text']}")
            lines.append(f"\n--- End of Transcript ---")
            return "\n".join(lines)
    
    async def serve_web_files(self, request):
        """Serve static web files."""
        file_path = request.match_info.get('path', 'index.html')
        
        # Security: prevent directory traversal
        if '..' in file_path or file_path.startswith('/'):
            raise web.HTTPForbidden()
        
        # Resolve file path
        web_dir = Path(__file__).parent / 'web'
        full_path = web_dir / file_path
        
        if not full_path.exists() or not full_path.is_file():
            raise web.HTTPNotFound()
        
        # Determine content type
        content_types = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.svg': 'image/svg+xml',
        }
        content_type = content_types.get(full_path.suffix, 'text/plain')
        
        return web.FileResponse(full_path, headers={'Content-Type': content_type})


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Real-time Audio Transcription & Semantic Prediction Streaming Server"
    )
    
    # Server options
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    
    # Audio options
    parser.add_argument("--device", type=int, default=None, help="Audio device index")
    parser.add_argument("--list-devices", action="store_true", help="List audio devices and exit")
    parser.add_argument("--sr", type=int, default=16000, help="Sample rate (Hz)")
    
    # Whisper options
    parser.add_argument("--whisper-model", default="mlx-community/whisper-large-v3-turbo",
                       help="Whisper model path or HuggingFace repo")
    parser.add_argument("--window-s", type=float, default=8.0,
                       help="Transcription window in seconds")
    parser.add_argument("--step-s", type=float, default=2.0,
                       help="Slide step in seconds")
    parser.add_argument("--lang", default="ja", help="Language code")
    
    # LLM options
    parser.add_argument("--llm-url", default="http://127.0.0.1:8080/v1/chat/completions",
                       help="LLM server URL")
    parser.add_argument("--llm-model", default="lfm2.5-jp", help="LLM model name")
    parser.add_argument("--update-every-lines", type=int, default=3,
                       help="Update LLM predictions every N transcript lines")
    parser.add_argument("--max-tokens", type=int, default=180, help="LLM max tokens")
    parser.add_argument("--temperature", type=float, default=0.2, help="LLM temperature")
    
    args = parser.parse_args()
    
    # List devices and exit
    if args.list_devices:
        list_input_devices()
        return
    
    # Validate arguments
    if args.step_s <= 0 or args.window_s <= 0 or args.step_s >= args.window_s:
        parser.error("Require 0 < step-s < window-s")
    
    logger.info("=" * 70)
    logger.info("Real-time Audio Transcription & Semantic Prediction Server")
    logger.info("=" * 70)
    logger.info(f"Server: http://{args.host}:{args.port}")
    logger.info(f"Whisper model: {args.whisper_model}")
    logger.info(f"LLM: {args.llm_url} (model: {args.llm_model})")
    logger.info(f"Audio: device={args.device}, sr={args.sr}Hz")
    logger.info(f"Window: {args.window_s}s, Step: {args.step_s}s, Language: {args.lang}")
    logger.info("=" * 70)
    logger.info("Starting server...")
    
    # Create server instance
    server = StreamingServer(args)
    
    # Create aiohttp app
    app = web.Application()
    
    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    
    # Add routes
    app.router.add_get('/ws', server.websocket_handler)
    app.router.add_get('/', server.serve_web_files)
    app.router.add_get('/{path:.*}', server.serve_web_files)
    
    # Configure CORS on all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    # Run server
    try:
        logger.info(f"Server started at http://{args.host}:{args.port}")
        logger.info("Open your browser and navigate to the URL above")
        logger.info("Press Ctrl+C to stop")
        web.run_app(app, host=args.host, port=args.port, print=None)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        if server.is_recording:
            server.stop_recording()
        logger.info("Server stopped")


if __name__ == "__main__":
    main()
