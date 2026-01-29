"""LLM-based semantic prediction from transcripts."""
import logging
import json
import time
import re
from typing import Dict, Optional, List, Any, Tuple
import requests

logger = logging.getLogger(__name__)

SYSTEM = (
    "あなたは日本語会話の解析器です。"
    "必ず1行の生JSONのみを出力。"
    "``` やコードフェンス、説明文は禁止。"
    "JSON文字列内に改行は禁止（必要ならスペースに置換）。"
    "常に正しいJSONにする。"
)


class SemanticPredictor:
    """
    LLM-based semantic prediction from transcripts.
    
    Maintains global conversation state and generates predictions including:
    - Keywords: Important keywords from conversation
    - Next Terms: Words/phrases likely to appear next
    - Summary: Running summary of conversation
    """
    
    def __init__(
        self,
        llm_url: str,
        llm_model: str,
        max_tokens: int = 180,
        temperature: float = 0.2,
        update_every_lines: int = 3,
        max_chunk_chars: int = 900
    ):
        """
        Initialize semantic predictor.
        
        Args:
            llm_url: LLM API endpoint URL
            llm_model: LLM model name
            max_tokens: Maximum tokens per LLM call
            temperature: LLM temperature
            update_every_lines: Update predictions every N lines
            max_chunk_chars: Maximum characters per chunk
        """
        self.llm_url = llm_url
        self.llm_model = llm_model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.update_every_lines = update_every_lines
        self.max_chunk_chars = max_chunk_chars
        
        # Global conversation state
        self.running_summary = ""
        self.running_keywords: List[str] = []
        self.running_next: List[str] = []
        
        # New chunk buffer
        self.new_chunk_lines: List[str] = []
        self.lines_since_update = 0
        
        logger.info(f"SemanticPredictor initialized: url={llm_url}, model={llm_model}, "
                   f"update_every={update_every_lines} lines")
    
    def add_transcript_line(self, line: str) -> Optional[Dict]:
        """
        Add new transcript line.
        
        Args:
            line: Transcript line with timestamp and text
        
        Returns:
            Prediction dict if threshold reached, None otherwise
        """
        self.new_chunk_lines.append(line)
        self.lines_since_update += 1
        
        if self.lines_since_update >= self.update_every_lines:
            return self.force_update()
        
        return None
    
    def force_update(self) -> Dict:
        """
        Force prediction update with current buffer.
        
        Returns:
            Prediction dictionary with keywords, next_terms, summary, and metrics
        """
        new_chunk = "\n".join(self.new_chunk_lines).strip()
        if not new_chunk:
            return self._empty_prediction()
        
        # Limit chunk size
        if len(new_chunk) > self.max_chunk_chars:
            new_chunk = new_chunk[-self.max_chunk_chars:]
        
        # Call LLM
        result = self._call_llm(new_chunk)
        
        # Update global state
        if result["ok"]:
            llm_data = result["llm"]
            self.running_keywords = llm_data.get("keywords", []) or self.running_keywords
            self.running_next = llm_data.get("next_terms", []) or self.running_next
            if llm_data.get("summary"):
                self.running_summary = llm_data["summary"]
        
        # Reset buffer
        self.new_chunk_lines = []
        self.lines_since_update = 0
        
        return {
            "keywords": self.running_keywords,
            "next_terms": self.running_next,
            "summary": self.running_summary,
            "metrics": result.get("metrics", {}),
            "ok": result["ok"],
            "error": result.get("error", "")
        }
    
    def reset(self) -> None:
        """Clear all conversation state."""
        self.running_summary = ""
        self.running_keywords = []
        self.running_next = []
        self.new_chunk_lines = []
        self.lines_since_update = 0
        logger.info("SemanticPredictor reset")
    
    def _call_llm(self, new_chunk: str) -> Dict:
        """
        Call LLM and parse response robustly.
        
        Args:
            new_chunk: New transcript chunk to process
        
        Returns:
            Dictionary with llm data, metrics, ok status, and error
        """
        prompt = self._build_update_prompt(new_chunk)
        
        # 1) Streaming attempt (for metrics)
        try:
            raw1, m1 = self._call_chat(prompt, stream=True)
            parsed1, err1 = self._parse_json_robust(raw1)
            if parsed1 is not None:
                return {
                    "llm": parsed1,
                    "metrics": m1,
                    "ok": True,
                    "attempt": "stream",
                    "error": ""
                }
        except Exception as e:
            logger.error(f"LLM streaming call failed: {e}")
            err1 = str(e)
            m1 = {}
        
        # 2) Non-stream repair retry
        try:
            repair_prompt = (
                "次の出力は壊れたJSONです。正しい1行JSONに直してください。JSON以外は禁止。\n\n"
                f"壊れた出力:\n{raw1}"
            )
            raw2, m2 = self._call_chat(repair_prompt, stream=False)
            parsed2, err2 = self._parse_json_robust(raw2)
            if parsed2 is not None:
                m2["retry_from"] = "stream_failed"
                return {
                    "llm": parsed2,
                    "metrics": m2,
                    "ok": True,
                    "attempt": "nonstream_repair",
                    "error": err1
                }
        except Exception as e:
            logger.error(f"LLM retry call failed: {e}")
            err2 = str(e)
        
        # 3) Fallback
        return {
            "llm": {
                "keywords": self.running_keywords,
                "next_terms": self.running_next,
                "summary": self.running_summary or ""
            },
            "metrics": m1,
            "ok": False,
            "attempt": "failed",
            "error": f"stream={err1}; retry={err2 if 'err2' in locals() else 'not_attempted'}"
        }
    
    def _build_update_prompt(self, new_chunk: str) -> str:
        """Build prompt for LLM update."""
        return f"""
これまでの会話の要約（更新前）:
{self.running_summary if self.running_summary else "(なし)"}

新しく追加された書き起こし（この部分だけ）:
{new_chunk}

タスク:
- keywords: 会話全体（ここまで）の重要キーワード 5〜12個
- next_terms: 次に出現しそうな単語/短いフレーズ 5〜12個
- summary: 会話全体（ここまで）の要約 1〜2文（1行）

必ず1行のJSONのみ:
{{"keywords":["..."],"next_terms":["..."],"summary":"..."}}
""".strip()
    
    def _call_chat(self, user_content: str, stream: bool) -> Tuple[str, Dict[str, Any]]:
        """
        Make chat completion API call.
        
        Args:
            user_content: User message content
            stream: Whether to stream response
        
        Returns:
            Tuple of (response_text, metrics_dict)
        """
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_content}
        ]
        
        payload = {
            "model": self.llm_model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream,
        }
        
        t0 = time.perf_counter()
        first_token_t = None
        text_out = ""
        
        if stream:
            with requests.post(self.llm_url, json=payload, stream=True, timeout=30) as r:
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
            r = requests.post(self.llm_url, json=payload, timeout=30)
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
    
    def _parse_json_robust(self, raw: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Robustly parse JSON from LLM output.
        
        Args:
            raw: Raw LLM output
        
        Returns:
            Tuple of (parsed_dict or None, error_message)
        """
        if not raw or not raw.strip():
            return None, "empty_output"
        
        t = raw.strip().replace("```json", "").replace("```", "").strip()
        js = self._extract_first_balanced_json(t)
        if not js:
            return None, "no_json_found"
        
        js = js.replace(""", '"').replace(""", '"')
        js = re.sub(r",\s*([}\]])", r"\1", js)
        js = self._escape_newlines_inside_strings(js)
        
        try:
            obj = json.loads(js)
            if not isinstance(obj, dict):
                return None, "json_not_object"
            return obj, ""
        except Exception as e:
            return None, f"json_parse_failed: {type(e).__name__}: {e}"
    
    def _extract_first_balanced_json(self, s: str) -> Optional[str]:
        """Extract first balanced JSON object from string."""
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
    
    def _escape_newlines_inside_strings(self, s: str) -> str:
        """Escape newlines inside JSON strings."""
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
    
    def _empty_prediction(self) -> Dict:
        """Return empty prediction dictionary."""
        return {
            "keywords": self.running_keywords,
            "next_terms": self.running_next,
            "summary": self.running_summary,
            "metrics": {},
            "ok": True,
            "error": ""
        }
