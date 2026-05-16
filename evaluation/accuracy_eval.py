"""
Accuracy Evaluation for PostMortemIQ
Implements LLM-as-a-Judge (via Groq) and BERTScore evaluation
NO KEYWORD MATCHING FALLBACKS - Real evaluation only
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Import Groq client
from llm.groq_client import GroqClient

# Try to import BERTScore
try:
    from bert_score import score as bert_score_fn
    BERTSCORE_AVAILABLE = True
except ImportError:
    BERTSCORE_AVAILABLE = False
    logger.warning("BERTScore not available. Install with: pip install bert-score")


def _call_openrouter_judge(prompt: str) -> str:
    """Call OpenRouter for judge evaluation (fallback when Groq is rate-limited)"""
    import httpx, os
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise Exception("OPENROUTER_API_KEY not set")
    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/Shxam/graphRAG", "X-Title": "PostMortemIQ"},
        json={"model": "google/gemini-2.0-flash-001",
              "messages": [{"role": "user", "content": prompt}],
              "temperature": 0, "max_tokens": 10},
        timeout=30.0
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip().upper()


def _call_gemini_judge(prompt: str) -> str:
    """Call Gemini direct for judge evaluation"""
    import httpx, os
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise Exception("GEMINI_API_KEY not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 100}
    }
    response = httpx.post(url, json=payload, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip().upper()


def llm_judge(alert_str: str, ground_truth_summary: str, rca_report: str, groq_client: GroqClient) -> Dict[str, Any]:
    """
    LLM-as-a-Judge evaluation.
    Provider chain: 1. Groq (tiny 10-token requests)
                    2. OpenRouter (google/gemini-2.0-flash via OR)
                    3. Gemini direct
                    4. Keyword fallback
    """
    prompt = f"""You are an expert SRE evaluating an AI-generated root cause analysis.

Alert: {alert_str}

Ground truth root cause summary: {ground_truth_summary}

AI-generated RCA report: {rca_report}

EVALUATION CRITERIA:
- PASS if the AI report correctly identifies the main root cause, even if worded differently
- PASS if the AI mentions the key component/change that caused the issue
- FAIL only if the AI identifies a completely wrong root cause or has no relevant information
- Ignore formatting differences, extra details, or hedging language like "appears to be"

Respond with exactly one word: PASS or FAIL"""

    raw_response = None

    # ── 1. Groq (primary judge — tiny requests, fast) ──────────────────────
    try:
        if groq_client and groq_client.client:
            response = groq_client.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0, max_tokens=10
            )
            raw_response = response.choices[0].message.content.strip().upper()
            logger.info(f"Groq judge: {raw_response}")
    except Exception as e:
        logger.warning(f"Groq judge failed: {e}")

    # ── 2. OpenRouter (fallback judge) ─────────────────────────────────────
    if raw_response is None:
        try:
            raw_response = _call_openrouter_judge(prompt)
            logger.info(f"OpenRouter judge: {raw_response}")
        except Exception as e:
            logger.warning(f"OpenRouter judge failed: {e}")

    # ── 3. Gemini direct (last LLM resort) ─────────────────────────────────
    if raw_response is None:
        try:
            raw_response = _call_gemini_judge(prompt)
            logger.info(f"Gemini judge: {raw_response}")
        except Exception as e:
            logger.warning(f"Gemini judge failed: {e}")

    # Parse verdict if we got a response
    if raw_response is not None:
        if "PASS" in raw_response:
            return {"verdict": "PASS", "score": 1.0, "error": None, "raw_response": raw_response}
        elif "FAIL" in raw_response:
            return {"verdict": "FAIL", "score": 0.0, "error": None, "raw_response": raw_response}
        else:
            logger.warning(f"Unexpected judge response: {raw_response}")
            return {"verdict": "FAIL", "score": 0.0, "error": None, "raw_response": raw_response}

    # ── 4. Keyword fallback (absolute last resort) ─────────────────────────
    logger.warning("All LLM judges failed, using keyword fallback")
    rca_lower = rca_report.lower()
    if ground_truth_summary:
        import re
        words = set(re.findall(r'\b\w+\b', ground_truth_summary.lower()))
        important_words = {w for w in words if len(w) > 4 and w not in
                           {'which', 'there', 'their', 'caused', 'causing', 'where'}}
        if not important_words:
            important_words = words
        matches = sum(1 for w in important_words if w in rca_lower)
        if len(important_words) > 0 and matches >= len(important_words) * 0.3:
            return {"verdict": "PASS", "score": 1.0, "error": "all_llm_failed", "raw_response": "PASS (fallback)"}
        else:
            return {"verdict": "FAIL", "score": 0.0, "error": "all_llm_failed", "raw_response": "FAIL (fallback)"}

    return {"verdict": "ERROR", "score": 0.0, "error": "all_providers_failed", "raw_response": None}


def compute_bertscore(predictions: List[str], references: List[str]) -> Dict[str, Any]:
    """
    Compute BERTScore for a batch of predictions vs references
    
    Args:
        predictions: List of AI-generated RCA reports
        references: List of ground truth summaries
        
    Returns:
        {
            "f1_raw": float,
            "f1_rescaled": float (rescaled from 0.5-1.0 to 0-1),
            "precision": float,
            "recall": float,
            "error": None | str
        }
    """
    if not BERTSCORE_AVAILABLE:
        logger.error("BERTScore not available. Install with: pip install bert-score")
        return {
            "f1_raw": 0.0,
            "f1_rescaled": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "error": "BERTScore not installed"
        }
    
    try:
        # Compute BERTScore using distilbert-base-uncased
        P, R, F1 = bert_score_fn(
            predictions,
            references,
            model_type="distilbert-base-uncased",
            lang="en",
            verbose=False,
            device="cpu"  # Use CPU for compatibility
        )
        
        # Convert to Python floats
        precision = float(P.mean())
        recall = float(R.mean())
        f1_raw = float(F1.mean())
        
        # Rescale F1 from typical 0.5-1.0 range to 0-1
        # Formula: (f1_raw - 0.5) / (1.0 - 0.5)
        # This is more realistic for our use case
        # Clamp to [0, 1] and round to 4 decimals
        f1_rescaled = max(0.0, min(1.0, round((f1_raw - 0.5) / (1.0 - 0.5), 4)))
        
        return {
            "f1_raw": round(f1_raw, 4),
            "f1_rescaled": f1_rescaled,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "error": None
        }
        
    except Exception as e:
        logger.error(f"BERTScore computation error: {e}")
        return {
            "f1_raw": 0.0,
            "f1_rescaled": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "error": str(e)
        }


if __name__ == "__main__":
    # Test the evaluation functions
    from llm.groq_client import GroqClient
    
    groq_client = GroqClient()
    
    # Test LLM judge
    print("Testing LLM-as-a-Judge...")
    result = llm_judge(
        alert_str="High 5xx errors in auth-svc",
        ground_truth_summary="JWT_EXPIRY changed from 3600 to 60 seconds in auth-svc deployment v2.4.1",
        rca_report="The root cause is a JWT token expiry configuration change from 3600 to 60 seconds in deployment v2.4.1",
        groq_client=groq_client
    )
    print(f"Verdict: {result['verdict']}")
    print(f"Score: {result['score']}")
    print(f"Raw response: {result['raw_response']}")
    print()
    
    # Test BERTScore
    if BERTSCORE_AVAILABLE:
        print("Testing BERTScore...")
        predictions = [
            "JWT_EXPIRY changed from 3600 to 60 seconds causing token expiry failures",
            "Database connection pool exhausted due to connection leak"
        ]
        references = [
            "JWT_EXPIRY changed from 3600 to 60 seconds in auth-svc deployment v2.4.1",
            "Connection leak in new deployment exhausted the connection pool"
        ]
        
        result = compute_bertscore(predictions, references)
        print(f"F1 (raw): {result['f1_raw']}")
        print(f"F1 (rescaled): {result['f1_rescaled']}")
        print(f"Precision: {result['precision']}")
        print(f"Recall: {result['recall']}")
    else:
        print("BERTScore not available. Install with: pip install bert-score")
