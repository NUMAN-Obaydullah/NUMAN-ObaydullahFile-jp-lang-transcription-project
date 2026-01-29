# Performance Benchmarking Guide

This guide explains how to benchmark and compare different LLM models for semantic prediction on Japanese transcription data.

## Overview

The benchmarking system allows you to:
- Compare multiple LLM models on identical transcript inputs
- Measure token output speed (tokens/second)
- Track time to first token (TTFT) and total generation time
- Evaluate output quality (keywords, next terms, summary)
- Generate comprehensive performance reports

## Quick Start

### 1. Prepare Transcript File

Create or use an existing transcript file with timestamped segments:

```
[    0.00s ->     4.50s] こんにちは、今日はプロジェクトの進捗について話し合いたいと思います
[    4.50s ->     8.20s] はい、先週から取り組んでいた新機能の開発が完了しました
...
```

Or use the sample:
```bash
cp sample_transcript.txt my_transcript.txt
```

### 2. Configure Models

Create a models configuration JSON file:

```json
{
  "models": [
    {
      "name": "LFM2.5-1.2B-JP",
      "url": "http://127.0.0.1:8080/v1/chat/completions",
      "model_id": "lfm2.5-jp",
      "max_tokens": 180,
      "temperature": 0.2
    },
    {
      "name": "Alternative Model",
      "url": "http://127.0.0.1:8081/v1/chat/completions",
      "model_id": "alternative-model",
      "max_tokens": 180,
      "temperature": 0.2
    }
  ]
}
```

Or use the example:
```bash
cp models_config.example.json models_config.json
# Edit models_config.json with your model configurations
```

### 3. Start Model Servers

Start each LLM server you want to benchmark:

```bash
# Terminal 1: LFM2.5-1.2B-JP
llama-server \
  --model path/to/lfm2.5-1.2b-jp.gguf \
  --port 8080 \
  --ctx-size 4096

# Terminal 2: Alternative model (if testing)
llama-server \
  --model path/to/alternative-model.gguf \
  --port 8081 \
  --ctx-size 4096
```

### 4. Run Benchmark

```bash
python benchmark_models.py \
  --transcript my_transcript.txt \
  --models models_config.json \
  --output benchmark_report.md
```

### 5. View Report

The benchmark will generate a detailed report:

```bash
cat benchmark_report.md
```

## Command-Line Options

```bash
python benchmark_models.py --help
```

**Options:**
- `--transcript PATH` (required): Path to transcript file
- `--models PATH` (required): Path to models config JSON
- `--output PATH`: Output report path (default: benchmark_report.md)
- `--format FORMAT`: Report format - markdown, json, or csv (default: markdown)

## Report Formats

### Markdown Format (Default)

Human-readable report with:
- Performance summary table
- Speed comparison analysis
- Detailed results for each model
- Keywords, next terms, and summaries

```bash
python benchmark_models.py \
  --transcript input.txt \
  --models config.json \
  --output report.md \
  --format markdown
```

### JSON Format

Machine-readable format for further analysis:

```bash
python benchmark_models.py \
  --transcript input.txt \
  --models config.json \
  --output report.json \
  --format json
```

### CSV Format

Spreadsheet-compatible format:

```bash
python benchmark_models.py \
  --transcript input.txt \
  --models config.json \
  --output report.csv \
  --format csv
```

## Metrics Explained

### Performance Metrics

**TTFT (Time to First Token):**
- Time from request start to first token generated
- Lower is better (indicates faster response start)
- Measured in milliseconds (ms)

**Total Time:**
- Complete time from request start to completion
- Includes TTFT + generation time
- Measured in seconds (s)

**Tokens per Second:**
- Average token generation speed
- Higher is better (indicates faster generation)
- Estimated: characters / 2.5 (for Japanese)

**Characters per Second:**
- Raw character generation speed
- Direct measurement from streaming output

### Quality Metrics

**Keywords Count:**
- Number of important keywords extracted
- Target: 5-12 keywords
- More isn't always better (relevance matters)

**Next Terms Count:**
- Number of predicted next terms
- Target: 5-12 terms
- Indicates prediction capability

**Summary Quality:**
- Coherence and completeness of summary
- Should be 1-2 sentences
- Manual evaluation recommended

## Model Configuration

### Required Fields

```json
{
  "name": "Model Display Name",
  "url": "http://host:port/v1/chat/completions",
  "model_id": "model-identifier"
}
```

### Optional Fields

```json
{
  "max_tokens": 180,      // Maximum tokens to generate
  "temperature": 0.2      // Sampling temperature
}
```

### Supported Model Types

The benchmark supports any model with OpenAI-compatible API:
- llama.cpp servers (llama-server)
- vLLM servers
- OpenAI API
- Any compatible endpoint

### Alternative Japanese Models

Consider testing:
1. **LFM2.5-1.2B-JP** (default)
   - Optimized for Japanese
   - Good balance of speed and quality

2. **GPT-4-turbo** (via OpenAI API)
   - High quality
   - Higher cost, slower

3. **Mistral models**
   - Multilingual support
   - Fast inference

4. **Claude models** (via Anthropic API)
   - High quality
   - Good Japanese support

## Example Benchmark Run

```bash
# Step 1: Create transcript from real recording
python realtime_whisper_v3_to_txt.py \
  --out test_transcript.txt \
  --model mlx-community/whisper-large-v3-turbo \
  --lang ja

# Step 2: Configure models to test
cat > benchmark_config.json << 'EOF'
{
  "models": [
    {
      "name": "LFM2.5-1.2B-JP",
      "url": "http://127.0.0.1:8080/v1/chat/completions",
      "model_id": "lfm2.5-jp",
      "max_tokens": 180,
      "temperature": 0.2
    }
  ]
}
EOF

# Step 3: Run benchmark
python benchmark_models.py \
  --transcript test_transcript.txt \
  --models benchmark_config.json \
  --output performance_report.md

# Step 4: View results
cat performance_report.md
```

## Interpreting Results

### Speed Comparison

Look for:
- **TTFT < 200ms**: Excellent responsiveness
- **Tokens/sec > 20**: Good generation speed for Japanese
- **Total time < 2s**: Fast enough for real-time applications

### Quality Assessment

Evaluate manually:
- **Keywords**: Should capture main topics discussed
- **Next Terms**: Should be contextually relevant
- **Summary**: Should be concise and accurate

### Trade-offs

Consider:
- Faster models may have lower quality
- Smaller models are faster but less capable
- Temperature affects both speed and quality

## Troubleshooting

### Model Server Not Running

**Error**: `Connection refused` or timeout

**Solution**:
- Check server is running: `curl http://localhost:8080/v1/models`
- Verify correct port in config
- Check firewall settings

### Out of Memory

**Error**: Model crashes or benchmark hangs

**Solution**:
- Use smaller model
- Reduce `max_tokens`
- Reduce context size in server
- Use quantized model (4-bit, 8-bit)

### Invalid JSON Response

**Error**: JSON parsing fails

**Solution**:
- Some models may not follow JSON format strictly
- The benchmark has robust parsing (extracts from text)
- Check model supports instruction following

### Slow Performance

**Issue**: Benchmark takes very long

**Solution**:
- Use GPU acceleration (`--n-gpu-layers`)
- Try turbo/fast model variant
- Reduce transcript length for testing
- Check system resources (CPU/RAM usage)

## Best Practices

### Fair Comparison

1. **Use identical input**: Same transcript for all models
2. **Same parameters**: Use same max_tokens, temperature
3. **Warm-up**: Run once to warm up models, then benchmark
4. **Multiple runs**: Average results across multiple runs
5. **Clean state**: Restart servers between benchmarks

### Transcript Selection

1. **Representative**: Use typical conversation data
2. **Length**: 10-20 lines for quick tests, 50+ for thorough
3. **Content**: Include domain-specific vocabulary
4. **Format**: Use consistent timestamp format

### Model Selection

1. **Baseline**: Always include your current production model
2. **Alternatives**: Test 2-3 promising alternatives
3. **Variants**: Compare different sizes/quantizations
4. **Budget**: Consider cost vs. performance

## Advanced Usage

### Batch Benchmarking

Test multiple transcripts:

```bash
for transcript in transcripts/*.txt; do
    python benchmark_models.py \
        --transcript "$transcript" \
        --models config.json \
        --output "reports/$(basename $transcript .txt).md"
done
```

### Automated Testing

Integrate into CI/CD:

```yaml
# .github/workflows/benchmark.yml
- name: Run benchmark
  run: |
    python benchmark_models.py \
      --transcript test_data.txt \
      --models ci_models.json \
      --output benchmark.json \
      --format json
```

### Custom Metrics

Extend `benchmark_models.py` to add:
- Latency percentiles (p50, p95, p99)
- Memory usage tracking
- GPU utilization monitoring
- Custom quality scoring

## Sample Report

Here's what a typical report looks like:

```markdown
# Performance Benchmark Report

**Date**: 2026-01-29 10:30:45
**Transcript**: sample_transcript.txt
**Models Tested**: 2

## Performance Summary

| Model | TTFT (ms) | Total (s) | Tokens/sec | Chars/sec | Keywords | Next Terms | Status |
|-------|-----------|-----------|------------|-----------|----------|------------|--------|
| LFM2.5-1.2B-JP | 125.5 | 0.98 | 35.2 | 88.1 | 8 | 10 | ✅ |
| Alternative Model | 98.3 | 1.25 | 28.4 | 71.0 | 7 | 9 | ✅ |

## Speed Comparison

- **Fastest**: LFM2.5-1.2B-JP (35.2 tokens/sec)
- **Slowest**: Alternative Model (28.4 tokens/sec)
- **Average**: 31.8 tokens/sec
- **Speed Ratio**: 1.24x

...
```

## Integration with Main System

The benchmark tool complements the main transcription system:

1. **Streaming Server**: Use for real-time production
2. **Benchmark Tool**: Use for model comparison and selection
3. **Workflow**: Benchmark → Select best model → Configure streaming server

## Future Enhancements

Potential additions:
- Real-time benchmarking (benchmark while streaming)
- Quality scoring algorithms (automated evaluation)
- Cost analysis (tokens * price per token)
- Confidence intervals and statistical significance
- Multi-threaded parallel benchmarking
- GPU memory profiling

## Support

For issues or questions:
- Check troubleshooting section above
- Review example configurations
- Test with sample_transcript.txt first
- Check model server logs for errors

---

**Remember**: Benchmarking helps you make informed decisions about model selection for your specific use case. Always consider the trade-offs between speed, quality, and cost.
