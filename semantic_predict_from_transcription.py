#!/usr/bin/env python3
"""
Global (whole-conversation) semantic prediction from transcript -> LFM2.5-1.2B-JP via llama-server.

Key idea:
- Maintain running_summary + running_keywords for the WHOLE conversation so far.
- Every N lines (or in final-only mode), update the state using only the NEW chunk since last update.
- Output JSON guaranteed by: stream attempt -> robust parse -> non-stream repair retry.

Supports transcript formats:
1) Whisper: [  12.00s ->  17.00s] text
2) Gemini : 0 - 4s: text
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Iterator, Tuple

import requests

DEFAULT_URL = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_MODEL = "lfm2.5-jp"

SYSTEM = (
    "あなたは日本語会話の解析器です。"
    "必ず1行の生JSONのみを出力。"
    "``` やコードフェンス、説明文は禁止。"
    "JSON文字列内に改行は禁止（必要ならスペースに置換）。"
    "常に正しいJSONにする。"
)

# Whisper style: [ 12.34s] or [ 12.34s -> 56.78s]
TS_WHISPER = re.compile(r"\[\s*([0-9.]+)s(?:\s*->\s*([0-9.]+)s)?\]\s*(.*)$")
# Gemini style: 0 - 4s: text
TS_GEMINI = re.compile(r"^\s*([0-9.]+)\s*-\s*([0-9.]+)s:\s*(.*)$")

def normalize_line(line: str) -> Tuple[Optional[float], str, str]:
    """Returns (t_end, normalized_line, text_only)"""
    line = line.strip()
    if not line:
        return None, "", ""

    m = TS_WHISPER.match(line)
    if m:
        t0 = float(m.group(1))
        t1 = float(m.group(2)) if m.group(2) else t0
        text = m.group(3).strip()
        norm = f"[{t0:8.2f}s -> {t1:8.2f}s] {text}" if m.group(2) else f"[{t0:8.2f}s] {text}"
        return t1, norm, text

    g = TS_GEMINI.match(line)
    if g:
        t0 = float(g.group(1))
        t1 = float(g.group(2))
        text = g.group(3).strip()
        norm = f"[{t0:8.2f}s -> {t1:8.2f}s] {text}"
        return t1, norm, text

    return None, line, line


def iter_lines(path: Path, from_start: bool, follow: bool) -> Iterator[str]:
    while follow and not path.exists():
        time.sleep(0.2)
    with path.open("r", encoding="utf-8") as f:
        f.seek(0, 0 if from_start else 2)
        while True:
            line = f.readline()
            if line:
                yield line.rstrip("\n")
            elif follow:
                time.sleep(0.1)
            else:
                return


def extract_first_balanced_json(s: str) -> Optional[str]:
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i + 1]
    return None


def escape_newlines_inside_strings(s: str) -> str:
    out = []
    in_str = False
    esc = False
    for ch in s:
        if in_str:
            if esc:
                out.append(ch)
                esc = False
                continue
            if ch == "\\":
                out.append(ch)
                esc = True
                continue
            if ch == '"':
                out.append(ch)
                in_str = False
                continue
            if ch == "\n":
                out.append("\\n")
                continue
            if ch == "\r":
                out.append("\\r")
                continue
            if ch == "\t":
                out.append("\\t")
                continue
            out.append(ch)
        else:
            out.append(ch)
            if ch == '"':
                in_str = True
    return "".join(out)


def parse_json_robust(raw: str) -> Tuple[Optional[Dict[str, Any]], str]:
    if not raw or not raw.strip():
        return None, "empty_output"
    t = raw.strip().replace("```json", "").replace("```", "").strip()
    js = extract_first_balanced_json(t)
    if not js:
        return None, "no_json_found"
    js = js.replace("“", '"').replace("”", '"')
    js = re.sub(r",\s*([}\]])", r"\1", js)
    js = escape_newlines_inside_strings(js)
    try:
        obj = json.loads(js)
        if not isinstance(obj, dict):
            return None, "json_not_object"
        return obj, ""
    except Exception as e:
        return None, f"json_parse_failed: {type(e).__name__}: {e}"


def call_chat(url: str, model: str, messages: List[Dict[str, str]],
              max_tokens: int, temperature: float, stream: bool) -> Tuple[str, Dict[str, Any]]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    t0 = time.perf_counter()
    first_token_t = None
    text_out = ""

    if stream:
        with requests.post(url, json=payload, stream=True, timeout=300) as r:
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
                    text_out += delta
    else:
        r = requests.post(url, json=payload, timeout=300)
        r.raise_for_status()
        obj = r.json()
        text_out = obj.get("choices", [{}])[0].get("message", {}).get("content", "") or ""

    t1 = time.perf_counter()
    ttft_ms = None if first_token_t is None else (first_token_t - t0) * 1000.0
    gen_s = t1 - (first_token_t or t0)
    cps = (len(text_out) / gen_s) if gen_s > 0 else None

    return text_out, {
        "ttft_ms": ttft_ms,
        "total_s": t1 - t0,
        "gen_s": gen_s,
        "chars_per_sec": cps,
        "stream": stream,
    }


def build_update_prompt(running_summary: str, new_chunk: str) -> str:
    return f"""
これまでの会話の要約（更新前）:
{running_summary if running_summary else "(なし)"}

新しく追加された書き起こし（この部分だけ）:
{new_chunk}

タスク:
- keywords: 会話全体（ここまで）の重要キーワード 5〜12個
- next_terms: 次に出現しそうな単語/短いフレーズ 5〜12個
- summary: 会話全体（ここまで）の要約 1〜2文（1行）

必ず1行のJSONのみ:
{{"keywords":["..."],"next_terms":["..."],"summary":"..."}}
""".strip()


def call_llm_update_state(url: str, model: str, running_summary: str, new_chunk: str,
                          max_tokens: int, temperature: float, dump_dir: str = "/tmp") -> Dict[str, Any]:
    # 1) streaming attempt (for metrics)
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": build_update_prompt(running_summary, new_chunk)},
    ]
    raw1, m1 = call_chat(url, model, msgs, max_tokens=max_tokens, temperature=temperature, stream=True)
    parsed1, err1 = parse_json_robust(raw1)
    if parsed1 is not None:
        return {"llm": parsed1, "metrics": m1, "ok": True, "attempt": "stream", "error": ""}

    # dump
    try:
        Path(dump_dir, f"semantic_raw_stream_{int(time.time())}.txt").write_text(raw1, encoding="utf-8")
    except Exception:
        pass

    # 2) non-stream repair retry (high reliability)
    repair_msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user",
         "content": "次の出力は壊れたJSONです。正しい1行JSONに直してください。JSON以外は禁止。\n\n壊れた出力:\n" + raw1},
    ]
    raw2, m2 = call_chat(url, model, repair_msgs, max_tokens=max_tokens, temperature=0.0, stream=False)
    parsed2, err2 = parse_json_robust(raw2)
    if parsed2 is not None:
        m2["retry_from"] = "stream_failed"
        return {"llm": parsed2, "metrics": m2, "ok": True, "attempt": "nonstream_repair", "error": err1}

    try:
        Path(dump_dir, f"semantic_raw_retry_{int(time.time())}.txt").write_text(raw2, encoding="utf-8")
    except Exception:
        pass

    return {
        "llm": {"keywords": [], "next_terms": [], "summary": running_summary or ""},
        "metrics": m1,
        "ok": False,
        "attempt": "failed",
        "error": f"stream={err1}; retry={err2}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--out-events", required=True, help="events JSONL (state updates over time)")
    ap.add_argument("--out-final", required=True, help="final JSON (whole conversation summary)")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)

    ap.add_argument("--from-start", action="store_true")
    ap.add_argument("--follow", action="store_true")

    ap.add_argument("--update-every-lines", type=int, default=6, help="update global state every N lines")
    ap.add_argument("--max-newchunk-chars", type=int, default=900, help="send only latest chunk chars per update")
    ap.add_argument("--max-tokens", type=int, default=180)
    ap.add_argument("--temperature", type=float, default=0.2)

    ap.add_argument("--dedup", action="store_true")
    ap.add_argument("--final-only", action="store_true", help="read whole file then do one final summary update")
    args = ap.parse_args()

    transcript_path = Path(args.transcript).expanduser().resolve()
    out_events = Path(args.out_events).expanduser().resolve()
    out_final = Path(args.out_final).expanduser().resolve()
    out_events.parent.mkdir(parents=True, exist_ok=True)
    out_final.parent.mkdir(parents=True, exist_ok=True)

    running_summary = ""
    running_keywords: List[str] = []
    running_next: List[str] = []

    new_chunk_lines: List[str] = []
    line_seen = 0
    updates = 0
    prev_text = None

    def flush_update(last_t: Optional[float], last_line: str):
        nonlocal running_summary, running_keywords, running_next, updates, new_chunk_lines
        new_chunk = "\n".join(new_chunk_lines).strip()
        if not new_chunk:
            return

        # limit chunk size
        if len(new_chunk) > args.max_newchunk_chars:
            new_chunk = new_chunk[-args.max_newchunk_chars:]

        res = call_llm_update_state(
            url=args.url,
            model=args.model,
            running_summary=running_summary,
            new_chunk=new_chunk,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )

        llm = res["llm"]
        running_keywords = llm.get("keywords", []) or running_keywords
        running_next = llm.get("next_terms", []) or running_next
        if llm.get("summary"):
            running_summary = llm["summary"]

        event = {
            "t_audio": last_t,
            "asr_line": last_line,
            "new_chunk": new_chunk,
            "llm": {"keywords": running_keywords, "next_terms": running_next, "summary": running_summary},
            "metrics": res["metrics"],
            "ok": res["ok"],
            "attempt": res["attempt"],
            "error": res["error"],
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with out_events.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        updates += 1
        new_chunk_lines = []

    # FINAL-ONLY: read entire file, then summarize once (whole conversation)
    if args.final_only:
        last_t, last_norm, _ = None, "", ""
        for raw in iter_lines(transcript_path, from_start=True, follow=False):
            if not raw or raw.startswith("---"):
                continue
            t, norm, text = normalize_line(raw)
            if not text:
                continue
            if args.dedup and prev_text == text:
                continue
            prev_text = text
            last_t, last_norm = t, norm
            new_chunk_lines.append(norm)

        # One update call (whole conversation)
        flush_update(last_t, last_norm)

        final_obj = {
            "keywords": running_keywords,
            "next_terms": running_next,
            "summary": running_summary,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        out_final.write_text(json.dumps(final_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Wrote final summary:", out_final)
        return

    # STREAM/BATCH incremental global summary updates
    last_t, last_norm = None, ""
    for raw in iter_lines(transcript_path, from_start=args.from_start, follow=args.follow):
        if not raw or raw.startswith("---"):
            continue
        t, norm, text = normalize_line(raw)
        if not text:
            continue
        if args.dedup and prev_text == text:
            continue
        prev_text = text

        line_seen += 1
        last_t, last_norm = t, norm
        new_chunk_lines.append(norm)

        if args.update_every_lines > 0 and (line_seen % args.update_every_lines) == 0:
            flush_update(last_t, last_norm)

    # end of file: flush remaining
    flush_update(last_t, last_norm)

    final_obj = {
        "keywords": running_keywords,
        "next_terms": running_next,
        "summary": running_summary,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    out_final.write_text(json.dumps(final_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote final summary:", out_final)


if __name__ == "__main__":
    main()
