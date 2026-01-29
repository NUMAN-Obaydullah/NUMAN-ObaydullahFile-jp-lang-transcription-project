# Performance Benchmarking - Example Workflow

This document shows a complete example workflow for benchmarking LLM models.

## Prerequisites

1. Have transcription data available
2. LLM server(s) running on different ports

## Step-by-Step Example

### Step 1: Generate Transcription Data

Use the real-time transcription system to create a test transcript:

```bash
# Option A: Use sample data
cp sample_transcript.txt test_transcript.txt

# Option B: Create your own from audio
python realtime_whisper_v3_to_txt.py \
  --out test_transcript.txt \
  --model mlx-community/whisper-large-v3-turbo \
  --lang ja \
  --device 0
# Speak for 30-60 seconds, then Ctrl+C
```

### Step 2: Start LLM Servers

Start each model you want to benchmark on different ports:

```bash
# Terminal 1: LFM2.5-1.2B-JP (Primary)
llama-server \
  --model ~/models/lfm2.5-1.2b-jp-q4.gguf \
  --port 8080 \
  --ctx-size 4096 \
  --n-gpu-layers 35

# Terminal 2: Alternative Model (if testing)
llama-server \
  --model ~/models/alternative-model-q4.gguf \
  --port 8081 \
  --ctx-size 4096 \
  --n-gpu-layers 35
```

### Step 3: Create Model Configuration

Create a JSON file with models to test:

```bash
cat > benchmark_config.json << 'EOF'
{
  "models": [
    {
      "name": "LFM2.5-1.2B-JP Q4",
      "url": "http://127.0.0.1:8080/v1/chat/completions",
      "model_id": "lfm2.5-jp",
      "max_tokens": 180,
      "temperature": 0.2
    },
    {
      "name": "Alternative Model Q4",
      "url": "http://127.0.0.1:8081/v1/chat/completions",
      "model_id": "alternative-model",
      "max_tokens": 180,
      "temperature": 0.2
    }
  ]
}
EOF
```

### Step 4: Run Benchmark

Execute the benchmark:

```bash
python benchmark_models.py \
  --transcript test_transcript.txt \
  --models benchmark_config.json \
  --output benchmark_report.md \
  --format markdown
```

Expected output:
```
======================================================================
PERFORMANCE BENCHMARK
======================================================================
Transcript: test_transcript.txt
Lines: 10
Characters: 519
Models to test: 2
======================================================================

======================================================================
Benchmarking: LFM2.5-1.2B-JP Q4
URL: http://127.0.0.1:8080/v1/chat/completions
Model ID: lfm2.5-jp
======================================================================
✓ TTFT: 125.5ms
✓ Total time: 0.98s
✓ Characters: 220 (224.5 chars/sec)
✓ Tokens (est): 88 (89.8 tokens/sec)
✓ Keywords: 8 - ['プロジェクト', '進捗', '開発']
✓ Next terms: 10 - ['テスト', 'デプロイ', '改善']
✓ Summary: プロジェクトの進捗について話し合い、新機能開発が完了した...

======================================================================
Benchmarking: Alternative Model Q4
URL: http://127.0.0.1:8081/v1/chat/completions
Model ID: alternative-model
======================================================================
...
```

### Step 5: View Results

#### View Markdown Report

```bash
cat benchmark_report.md
```

Sample output:
```markdown
# Performance Benchmark Report

**Date**: 2026-01-29 10:30:45
**Transcript**: test_transcript.txt
**Models Tested**: 2

## Performance Summary

| Model | TTFT (ms) | Total (s) | Tokens/sec | Chars/sec | Keywords | Next Terms | Status |
|-------|-----------|-----------|------------|-----------|----------|------------|--------|
| LFM2.5-1.2B-JP Q4 | 125.5 | 0.98 | 89.8 | 224.5 | 8 | 10 | ✅ |
| Alternative Model Q4 | 98.3 | 1.15 | 75.2 | 188.0 | 7 | 9 | ✅ |

## Speed Comparison

- **Fastest**: LFM2.5-1.2B-JP Q4 (89.8 tokens/sec)
- **Slowest**: Alternative Model Q4 (75.2 tokens/sec)
- **Average**: 82.5 tokens/sec
- **Speed Ratio**: 1.19x
```

#### Export to JSON for Analysis

```bash
python benchmark_models.py \
  --transcript test_transcript.txt \
  --models benchmark_config.json \
  --output benchmark_report.json \
  --format json

# Use jq to query results
cat benchmark_report.json | jq '.results[].tokens_per_sec'
```

#### Export to CSV for Excel

```bash
python benchmark_models.py \
  --transcript test_transcript.txt \
  --models benchmark_config.json \
  --output benchmark_report.csv \
  --format csv

# Open in spreadsheet software
open benchmark_report.csv
```

### Step 6: Analyze Results

Compare the results to determine:

1. **Speed**: Which model is fastest?
2. **Quality**: Which produces better keywords/summaries?
3. **Responsiveness**: Which has lower TTFT?
4. **Trade-offs**: Speed vs. quality considerations

### Step 7: Configure Production System

Use the best-performing model in your streaming server:

```bash
python streaming_server.py \
  --llm-url http://127.0.0.1:8080/v1/chat/completions \
  --llm-model lfm2.5-jp \
  --max-tokens 180 \
  --temperature 0.2
```

## Advanced Examples

### Batch Benchmarking

Test multiple transcripts:

```bash
#!/bin/bash
for transcript in transcripts/*.txt; do
    basename=$(basename "$transcript" .txt)
    python benchmark_models.py \
        --transcript "$transcript" \
        --models benchmark_config.json \
        --output "reports/${basename}_report.md"
done
```

### Automated Comparison

Compare different quantization levels:

```bash
cat > quantization_test.json << 'EOF'
{
  "models": [
    {
      "name": "LFM2.5 Q8",
      "url": "http://127.0.0.1:8080/v1/chat/completions",
      "model_id": "lfm2.5-jp"
    },
    {
      "name": "LFM2.5 Q4",
      "url": "http://127.0.0.1:8081/v1/chat/completions",
      "model_id": "lfm2.5-jp"
    },
    {
      "name": "LFM2.5 Q2",
      "url": "http://127.0.0.1:8082/v1/chat/completions",
      "model_id": "lfm2.5-jp"
    }
  ]
}
EOF

python benchmark_models.py \
  --transcript test_transcript.txt \
  --models quantization_test.json \
  --output quantization_comparison.md
```

### Temperature Comparison

Test different temperatures on same model:

```bash
cat > temperature_test.json << 'EOF'
{
  "models": [
    {
      "name": "LFM2.5 Temp=0.0",
      "url": "http://127.0.0.1:8080/v1/chat/completions",
      "model_id": "lfm2.5-jp",
      "temperature": 0.0
    },
    {
      "name": "LFM2.5 Temp=0.2",
      "url": "http://127.0.0.1:8080/v1/chat/completions",
      "model_id": "lfm2.5-jp",
      "temperature": 0.2
    },
    {
      "name": "LFM2.5 Temp=0.7",
      "url": "http://127.0.0.1:8080/v1/chat/completions",
      "model_id": "lfm2.5-jp",
      "temperature": 0.7
    }
  ]
}
EOF
```

## Troubleshooting

### Models Not Responding

If benchmark shows connection errors:

```bash
# Check if servers are running
curl http://localhost:8080/v1/models
curl http://localhost:8081/v1/models

# Check server logs for errors
```

### Slow Performance

If benchmark is very slow:

```bash
# Check GPU usage
# Increase --n-gpu-layers in llama-server
# Use smaller model or higher quantization
# Reduce --max-tokens in config
```

### Inconsistent Results

For more reliable benchmarks:

```bash
# 1. Warm up models first
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"lfm2.5-jp","messages":[{"role":"user","content":"test"}]}'

# 2. Run benchmark multiple times
for i in {1..3}; do
    python benchmark_models.py \
        --transcript test.txt \
        --models config.json \
        --output "report_run${i}.md"
done

# 3. Average results
```

## Best Practices

1. **Fair Comparison**: Use identical transcripts and parameters
2. **Warm-up**: Run once to warm up models before benchmarking
3. **Multiple Runs**: Average results across 3-5 runs
4. **Representative Data**: Use typical conversation lengths and topics
5. **Clean State**: Restart servers between major benchmark sessions
6. **Document Context**: Record hardware specs, model versions, settings

## Next Steps

After benchmarking:

1. Select the best model based on your priorities (speed vs. quality)
2. Configure the streaming server with optimal settings
3. Test in real-time with actual audio
4. Monitor performance over longer sessions
5. Re-benchmark periodically with new model versions

## References

- Main documentation: [README.md](README.md)
- Detailed benchmarking guide: [BENCHMARKING.md](BENCHMARKING.md)
- Quick start: [QUICKSTART.md](QUICKSTART.md)

---

**Remember**: The "best" model depends on your specific requirements. Consider the trade-offs between speed, quality, memory usage, and cost for your use case.
