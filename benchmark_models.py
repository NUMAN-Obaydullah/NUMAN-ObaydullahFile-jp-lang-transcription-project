#!/usr/bin/env python3
"""
Performance Benchmarking Tool for LLM Models

Compares multiple LLM models (LFM2.5-1.2B-JP and alternatives) on identical
transcription inputs to measure:
- Token output speed (tokens/second)
- Time to first token (TTFT)
- Total generation time
- Output quality (keyword relevance, summary coherence)

Usage:
    python benchmark_models.py --transcript input.txt --models config.json --output report.md
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from dataclasses import dataclass, asdict
import statistics


@dataclass
class BenchmarkResult:
    """Results from a single model benchmark run."""
    model_name: str
    model_url: str
    transcript_lines: int
    total_time_s: float
    ttft_ms: Optional[float]
    chars_generated: int
    chars_per_sec: float
    tokens_estimated: int
    tokens_per_sec: float
    keywords: List[str]
    next_terms: List[str]
    summary: str
    error: Optional[str] = None


@dataclass
class ModelConfig:
    """Configuration for a model to benchmark."""
    name: str
    url: str
    model_id: str
    max_tokens: int = 180
    temperature: float = 0.2


class ModelBenchmarker:
    """Benchmarks multiple LLM models on transcription data."""
    
    def __init__(self, transcript_path: Path, models: List[ModelConfig]):
        """
        Initialize benchmarker.
        
        Args:
            transcript_path: Path to transcript file
            models: List of model configurations to benchmark
        """
        self.transcript_path = transcript_path
        self.models = models
        self.results: List[BenchmarkResult] = []
    
    def load_transcript(self) -> str:
        """Load transcript from file."""
        return self.transcript_path.read_text(encoding='utf-8')
    
    def build_prompt(self, transcript: str) -> str:
        """Build standardized prompt for all models."""
        return f"""
これまでの会話の書き起こし:
{transcript}

タスク:
- keywords: 会話全体の重要キーワード 5〜12個
- next_terms: 次に出現しそうな単語/短いフレーズ 5〜12個
- summary: 会話全体の要約 1〜2文（1行）

必ず1行のJSONのみ:
{{"keywords":["..."],"next_terms":["..."],"summary":"..."}}
""".strip()
    
    def call_model(self, config: ModelConfig, prompt: str) -> Dict[str, Any]:
        """
        Call a model with the given prompt and measure performance.
        
        Args:
            config: Model configuration
            prompt: Prompt text
        
        Returns:
            Dictionary with response and metrics
        """
        messages = [
            {
                "role": "system",
                "content": "あなたは日本語会話の解析器です。必ず1行の生JSONのみを出力。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        payload = {
            "model": config.model_id,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": True
        }
        
        t0 = time.perf_counter()
        first_token_t = None
        response_text = ""
        
        try:
            with requests.post(config.url, json=payload, stream=True, timeout=60) as r:
                r.raise_for_status()
                for raw in r.iter_lines(decode_unicode=False):
                    if not raw or not raw.startswith(b"data: "):
                        continue
                    data = raw[6:].strip()
                    if data == b"[DONE]":
                        break
                    obj = json.loads(data)
                    delta = obj.get("choices", [{}])[0].get("delta", {}).get("content") or ""
                    if delta:
                        if first_token_t is None:
                            first_token_t = time.perf_counter()
                        response_text += delta
        except Exception as e:
            return {
                "text": "",
                "error": str(e),
                "ttft_ms": None,
                "total_s": time.perf_counter() - t0,
                "chars_per_sec": 0
            }
        
        t1 = time.perf_counter()
        ttft_ms = (first_token_t - t0) * 1000.0 if first_token_t else None
        gen_s = t1 - (first_token_t or t0)
        chars_per_sec = len(response_text) / gen_s if gen_s > 0 else 0
        
        return {
            "text": response_text,
            "error": None,
            "ttft_ms": ttft_ms,
            "total_s": t1 - t0,
            "gen_s": gen_s,
            "chars_per_sec": chars_per_sec
        }
    
    def parse_response(self, text: str) -> Dict[str, Any]:
        """
        Parse model response to extract keywords, next_terms, summary.
        
        Args:
            text: Model response text
        
        Returns:
            Parsed data or empty defaults
        """
        # Try to find JSON in response
        text = text.strip()
        if "```" in text:
            # Remove code blocks
            text = text.replace("```json", "").replace("```", "")
        
        # Find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        
        if start >= 0 and end > start:
            json_str = text[start:end+1]
            try:
                data = json.loads(json_str)
                return {
                    "keywords": data.get("keywords", []),
                    "next_terms": data.get("next_terms", []),
                    "summary": data.get("summary", "")
                }
            except json.JSONDecodeError:
                pass
        
        # Return empty defaults
        return {
            "keywords": [],
            "next_terms": [],
            "summary": ""
        }
    
    def benchmark_model(self, config: ModelConfig, transcript: str) -> BenchmarkResult:
        """
        Run benchmark for a single model.
        
        Args:
            config: Model configuration
            transcript: Transcript text
        
        Returns:
            Benchmark result
        """
        print(f"\n{'='*70}")
        print(f"Benchmarking: {config.name}")
        print(f"URL: {config.url}")
        print(f"Model ID: {config.model_id}")
        print(f"{'='*70}")
        
        # Build prompt
        prompt = self.build_prompt(transcript)
        transcript_lines = len(transcript.split('\n'))
        
        # Call model
        response = self.call_model(config, prompt)
        
        if response["error"]:
            print(f"❌ Error: {response['error']}")
            return BenchmarkResult(
                model_name=config.name,
                model_url=config.url,
                transcript_lines=transcript_lines,
                total_time_s=response["total_s"],
                ttft_ms=response["ttft_ms"],
                chars_generated=0,
                chars_per_sec=0,
                tokens_estimated=0,
                tokens_per_sec=0,
                keywords=[],
                next_terms=[],
                summary="",
                error=response["error"]
            )
        
        # Parse response
        parsed = self.parse_response(response["text"])
        
        # Estimate tokens (rough: 1 token ≈ 2.5 chars for Japanese)
        chars_generated = len(response["text"])
        tokens_estimated = int(chars_generated / 2.5)
        tokens_per_sec = tokens_estimated / response["gen_s"] if response["gen_s"] > 0 else 0
        
        # Display results
        print(f"✓ TTFT: {response['ttft_ms']:.1f}ms" if response['ttft_ms'] else "✓ TTFT: N/A")
        print(f"✓ Total time: {response['total_s']:.2f}s")
        print(f"✓ Characters: {chars_generated} ({response['chars_per_sec']:.1f} chars/sec)")
        print(f"✓ Tokens (est): {tokens_estimated} ({tokens_per_sec:.1f} tokens/sec)")
        print(f"✓ Keywords: {len(parsed['keywords'])} - {parsed['keywords'][:3]}")
        print(f"✓ Next terms: {len(parsed['next_terms'])} - {parsed['next_terms'][:3]}")
        print(f"✓ Summary: {parsed['summary'][:60]}...")
        
        return BenchmarkResult(
            model_name=config.name,
            model_url=config.url,
            transcript_lines=transcript_lines,
            total_time_s=response["total_s"],
            ttft_ms=response["ttft_ms"],
            chars_generated=chars_generated,
            chars_per_sec=response["chars_per_sec"],
            tokens_estimated=tokens_estimated,
            tokens_per_sec=tokens_per_sec,
            keywords=parsed["keywords"],
            next_terms=parsed["next_terms"],
            summary=parsed["summary"],
            error=None
        )
    
    def run_benchmarks(self) -> List[BenchmarkResult]:
        """Run benchmarks for all configured models."""
        transcript = self.load_transcript()
        
        print(f"\n{'='*70}")
        print(f"PERFORMANCE BENCHMARK")
        print(f"{'='*70}")
        print(f"Transcript: {self.transcript_path}")
        print(f"Lines: {len(transcript.split(chr(10)))}")
        print(f"Characters: {len(transcript)}")
        print(f"Models to test: {len(self.models)}")
        print(f"{'='*70}")
        
        results = []
        for config in self.models:
            result = self.benchmark_model(config, transcript)
            results.append(result)
            time.sleep(1)  # Brief pause between models
        
        self.results = results
        return results
    
    def generate_report(self, output_path: Path, format: str = "markdown"):
        """
        Generate performance comparison report.
        
        Args:
            output_path: Output file path
            format: Report format (markdown, json, csv)
        """
        if not self.results:
            print("No results to report. Run benchmarks first.")
            return
        
        if format == "markdown":
            self._generate_markdown_report(output_path)
        elif format == "json":
            self._generate_json_report(output_path)
        elif format == "csv":
            self._generate_csv_report(output_path)
        else:
            print(f"Unknown format: {format}")
    
    def _generate_markdown_report(self, output_path: Path):
        """Generate Markdown format report."""
        lines = []
        lines.append("# Performance Benchmark Report")
        lines.append("")
        lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Transcript**: {self.transcript_path}")
        lines.append(f"**Models Tested**: {len(self.results)}")
        lines.append("")
        
        # Summary table
        lines.append("## Performance Summary")
        lines.append("")
        lines.append("| Model | TTFT (ms) | Total (s) | Tokens/sec | Chars/sec | Keywords | Next Terms | Status |")
        lines.append("|-------|-----------|-----------|------------|-----------|----------|------------|--------|")
        
        for result in self.results:
            ttft = f"{result.ttft_ms:.1f}" if result.ttft_ms else "N/A"
            status = "✅" if not result.error else "❌"
            lines.append(
                f"| {result.model_name} | {ttft} | {result.total_time_s:.2f} | "
                f"{result.tokens_per_sec:.1f} | {result.chars_per_sec:.1f} | "
                f"{len(result.keywords)} | {len(result.next_terms)} | {status} |"
            )
        
        lines.append("")
        
        # Speed comparison
        lines.append("## Speed Comparison")
        lines.append("")
        successful_results = [r for r in self.results if not r.error]
        if successful_results:
            fastest = max(successful_results, key=lambda r: r.tokens_per_sec)
            slowest = min(successful_results, key=lambda r: r.tokens_per_sec)
            avg_tokens_per_sec = statistics.mean(r.tokens_per_sec for r in successful_results)
            
            lines.append(f"- **Fastest**: {fastest.model_name} ({fastest.tokens_per_sec:.1f} tokens/sec)")
            lines.append(f"- **Slowest**: {slowest.model_name} ({slowest.tokens_per_sec:.1f} tokens/sec)")
            lines.append(f"- **Average**: {avg_tokens_per_sec:.1f} tokens/sec")
            lines.append(f"- **Speed Ratio**: {fastest.tokens_per_sec / slowest.tokens_per_sec:.2f}x")
        lines.append("")
        
        # Detailed results
        lines.append("## Detailed Results")
        lines.append("")
        
        for result in self.results:
            lines.append(f"### {result.model_name}")
            lines.append("")
            if result.error:
                lines.append(f"**Status**: ❌ Error - {result.error}")
            else:
                lines.append(f"**Status**: ✅ Success")
                lines.append(f"**URL**: {result.model_url}")
                lines.append(f"**TTFT**: {result.ttft_ms:.1f}ms" if result.ttft_ms else "**TTFT**: N/A")
                lines.append(f"**Total Time**: {result.total_time_s:.2f}s")
                lines.append(f"**Tokens/sec**: {result.tokens_per_sec:.1f}")
                lines.append(f"**Chars/sec**: {result.chars_per_sec:.1f}")
                lines.append("")
                lines.append("**Keywords**:")
                for kw in result.keywords:
                    lines.append(f"- {kw}")
                lines.append("")
                lines.append("**Next Terms**:")
                for term in result.next_terms:
                    lines.append(f"- {term}")
                lines.append("")
                lines.append(f"**Summary**: {result.summary}")
            lines.append("")
        
        # Write report
        output_path.write_text("\n".join(lines), encoding='utf-8')
        print(f"\n✓ Markdown report written to: {output_path}")
    
    def _generate_json_report(self, output_path: Path):
        """Generate JSON format report."""
        data = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "transcript": str(self.transcript_path),
            "results": [asdict(r) for r in self.results]
        }
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n✓ JSON report written to: {output_path}")
    
    def _generate_csv_report(self, output_path: Path):
        """Generate CSV format report."""
        lines = []
        lines.append("Model,URL,TTFT_ms,Total_s,Tokens_per_sec,Chars_per_sec,Num_Keywords,Num_NextTerms,Error")
        
        for result in self.results:
            ttft = f"{result.ttft_ms:.1f}" if result.ttft_ms else "N/A"
            error = result.error or ""
            lines.append(
                f'"{result.model_name}","{result.model_url}",{ttft},{result.total_time_s:.2f},'
                f'{result.tokens_per_sec:.1f},{result.chars_per_sec:.1f},'
                f'{len(result.keywords)},{len(result.next_terms)},"{error}"'
            )
        
        output_path.write_text("\n".join(lines), encoding='utf-8')
        print(f"\n✓ CSV report written to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark multiple LLM models on transcription data"
    )
    parser.add_argument("--transcript", required=True, help="Path to transcript file")
    parser.add_argument("--models", required=True, help="Path to models config JSON")
    parser.add_argument("--output", default="benchmark_report.md", help="Output report path")
    parser.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown",
                       help="Report format")
    
    args = parser.parse_args()
    
    # Load transcript
    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"Error: Transcript file not found: {transcript_path}")
        return 1
    
    # Load models config
    models_path = Path(args.models)
    if not models_path.exists():
        print(f"Error: Models config not found: {models_path}")
        return 1
    
    with open(models_path, 'r', encoding='utf-8') as f:
        models_data = json.load(f)
    
    models = [ModelConfig(**m) for m in models_data["models"]]
    
    if not models:
        print("Error: No models configured")
        return 1
    
    # Run benchmark
    benchmarker = ModelBenchmarker(transcript_path, models)
    benchmarker.run_benchmarks()
    
    # Generate report
    output_path = Path(args.output)
    benchmarker.generate_report(output_path, args.format)
    
    print("\n" + "="*70)
    print("BENCHMARK COMPLETE")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    exit(main())
