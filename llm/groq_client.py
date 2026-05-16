"""
Groq API Client for PostMortemIQ
Handles LLM inference calls with token tracking and multi-provider fallback
"""

import os
import sys
import time
from typing import Dict, Any
from dotenv import load_dotenv
import logging

# Add parent directory to path for utils import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Import structured logger
try:
    from utils.logger import log_groq_request
    STRUCTURED_LOGGING = True
except ImportError:
    STRUCTURED_LOGGING = False
    logger.warning("Structured logging not available")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("Warning: groq package not installed. Using mock responses.")


class AllProvidersExhausted(Exception):
    """Raised when all LLM providers have failed"""
    pass


class GroqClient:
    """Client for Groq LLM API with token tracking and multi-provider fallback"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.together_api_key = os.getenv("TOGETHER_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if GROQ_AVAILABLE and self.api_key:
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None
    
    def _call_gemini(self, prompt: str, max_tokens: int = 1024) -> Dict[str, Any]:
        """Call Google Gemini API (secondary pipeline provider)"""
        import httpx
        start_time = time.time()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": max_tokens}
        }
        response = httpx.post(url, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", len(prompt) // 4)
        output_tokens = usage.get("candidatesTokenCount", len(text) // 4)
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "response": text, "input_tokens": input_tokens,
            "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens,
            "latency_ms": latency_ms, "model": "gemini-2.5-flash", "provider": "gemini"
        }

    def call_llm(self, prompt: str, model: str = "llama-3.3-70b-versatile", max_retries: int = 3) -> Dict[str, Any]:
        """
        4-provider fallback chain for pipeline RCA calls:
        1. OpenRouter  (google/gemini-2.0-flash-001 - primary, fastest)
        2. Gemini      (gemini-2.5-flash - secondary)
        3. Groq        (llama-3.3-70b - tertiary, preserve for judge)
        4. Mock        (last resort)
        """
        import httpx
        start_time = time.time()

        # ── 1. OpenRouter (primary) ─────────────────────────────────────────
        if self.openrouter_api_key:
            try:
                resp = httpx.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/Shxam/graphRAG",
                        "X-Title": "PostMortemIQ"
                    },
                    json={
                        "model": "google/gemini-2.0-flash-001",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3, "max_tokens": 1024
                    },
                    timeout=45.0
                )
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                latency_ms = int((time.time() - start_time) * 1000)
                logger.info(f"OpenRouter succeeded ({latency_ms}ms)")
                return {
                    "response": text,
                    "input_tokens": usage.get("prompt_tokens", len(prompt) // 4),
                    "output_tokens": usage.get("completion_tokens", len(text) // 4),
                    "total_tokens": usage.get("total_tokens", (len(prompt) + len(text)) // 4),
                    "latency_ms": latency_ms,
                    "model": "google/gemini-2.0-flash-001", "provider": "openrouter"
                }
            except Exception as e:
                logger.warning(f"OpenRouter failed: {e}, trying Gemini")

        # ── 2. Gemini Direct (secondary) ────────────────────────────────────
        if self.gemini_api_key:
            try:
                result = self._call_gemini(prompt)
                logger.info(f"Gemini succeeded ({result['latency_ms']}ms)")
                return result
            except Exception as e:
                logger.warning(f"Gemini failed: {e}, trying Groq")

        # ── 3. Groq (tertiary) ──────────────────────────────────────────────
        if self.client:
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3, max_tokens=1024
                    )
                    latency_ms = int((time.time() - start_time) * 1000)
                    result = {
                        "response": response.choices[0].message.content,
                        "input_tokens": response.usage.prompt_tokens,
                        "output_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                        "latency_ms": latency_ms, "model": model,
                        "provider": "groq", "retry_count": attempt
                    }
                    if STRUCTURED_LOGGING:
                        log_groq_request(model=model, tokens=result["total_tokens"],
                            latency_ms=latency_ms, retry_count=attempt, success=True)
                    return result
                except Exception as e:
                    error_msg = str(e)
                    is_rate_limit = "rate" in error_msg.lower() or "429" in error_msg
                    is_last = attempt == max_retries - 1
                    if is_rate_limit and not is_last:
                        delay = 2 ** attempt
                        logger.warning(f"Groq rate limit (attempt {attempt+1}), retry in {delay}s")
                        time.sleep(delay)
                    elif is_last:
                        logger.error(f"Groq failed after {max_retries} attempts: {e}")
                        return self._mock_response(prompt, start_time)
                    else:
                        time.sleep(0.5)

        return self._mock_response(prompt, start_time)
    
    def call_llm_with_fallback(self, prompt: str) -> Dict[str, Any]:
        """
        Call LLM with automatic fallback across providers
        
        Fallback chain:
        1. Groq - llama-3.3-70b-versatile
        2. Together AI - meta-llama/Llama-3-70b-chat-hf
        3. OpenRouter - mistralai/mixtral-8x7b-instruct
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Dictionary with response, tokens, latency, and provider
            
        Raises:
            AllProvidersExhausted: If all providers fail
        """
        providers_tried = []
        
        # Try Groq first (reuses retry logic from call_llm)
        try:
            result = self.call_llm(prompt)
            if result.get("provider") != "mock":  # call_llm succeeded with real provider
                return result
            # If we got a mock response, Groq failed — try fallbacks
            providers_tried.append(("Groq", "Groq unavailable or all retries exhausted"))
        except Exception as e:
            providers_tried.append(("Groq", str(e)))
        
        # Try Together AI
        if self.together_api_key:
            try:
                result = self._call_together(prompt)
                return result
            except Exception as e:
                error_msg = str(e)
                providers_tried.append(("Together AI", error_msg))
                print(f"Together AI failed: {error_msg}")
        
        # Try OpenRouter
        if self.openrouter_api_key:
            try:
                result = self._call_openrouter(prompt)
                return result
            except Exception as e:
                error_msg = str(e)
                providers_tried.append(("OpenRouter", error_msg))
                print(f"OpenRouter failed: {error_msg}")
        
        # All providers failed
        summary = "\n".join([f"- {provider}: {error}" for provider, error in providers_tried])
        raise AllProvidersExhausted(
            f"All LLM providers exhausted. Attempts:\n{summary}"
        )
    
    def _call_groq(self, prompt: str) -> Dict[str, Any]:
        """Call Groq API"""
        start_time = time.time()
        
        if not self.client:
            raise Exception("Groq client not initialized")
        
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "response": response.choices[0].message.content,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "latency_ms": latency_ms,
            "model": "llama-3.3-70b-versatile",
            "provider": "groq"
        }
    
    def _call_together(self, prompt: str) -> Dict[str, Any]:
        """Call Together AI API"""
        import httpx
        start_time = time.time()
        
        response = httpx.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.together_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/Llama-3-70b-chat-hf",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1024
            },
            timeout=30.0
        )
        
        if response.status_code in [429, 503]:
            raise Exception(f"Rate limit or service unavailable: {response.status_code}")
        
        response.raise_for_status()
        data = response.json()
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "response": data["choices"][0]["message"]["content"],
            "input_tokens": data["usage"]["prompt_tokens"],
            "output_tokens": data["usage"]["completion_tokens"],
            "total_tokens": data["usage"]["total_tokens"],
            "latency_ms": latency_ms,
            "model": "meta-llama/Llama-3-70b-chat-hf",
            "provider": "together"
        }
    
    def _call_openrouter(self, prompt: str) -> Dict[str, Any]:
        """Call OpenRouter API"""
        import httpx
        start_time = time.time()
        
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Shxam/graphRAG",
                "X-Title": "PostMortemIQ"
            },
            json={
                "model": "mistralai/mixtral-8x7b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1024
            },
            timeout=30.0
        )
        
        if response.status_code in [429, 503]:
            raise Exception(f"Rate limit or service unavailable: {response.status_code}")
        
        response.raise_for_status()
        data = response.json()
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "response": data["choices"][0]["message"]["content"],
            "input_tokens": data["usage"]["prompt_tokens"],
            "output_tokens": data["usage"]["completion_tokens"],
            "total_tokens": data["usage"]["total_tokens"],
            "latency_ms": latency_ms,
            "model": "mistralai/mixtral-8x7b-instruct",
            "provider": "openrouter"
        }
    
    def _mock_response(self, prompt: str, start_time: float) -> Dict[str, Any]:
        """Generate mock response for testing without API"""
        input_tokens = len(prompt) // 4  # Rough estimate
        output_tokens = 150
        latency_ms = int((time.time() - start_time) * 1000)
        
        prompt_lower = prompt.lower()
        is_graphrag = "verified causal graph subgraph" in prompt_lower
        
        if "connection pool exhaustion" in prompt_lower or "api-svc" in prompt_lower or "database" in prompt_lower:
            if is_graphrag:
                mock_response = "The root cause is a connection leak introduced in deployment v2.1.0 of the api-svc. This exhausted the database connection pool, causing 500 errors. Affected services are api-svc and database."
            else:
                mock_response = "The issue might be high traffic causing the database to be overloaded. Affected service: database."
        else:
            if is_graphrag:
                mock_response = "The incident was caused by a configuration change to JWT_EXPIRY_SECONDS from 3600 to 60 seconds in deployment v2.4.1 of the auth-svc service. This caused authentication tokens to expire faster, affecting auth-svc, payment-svc, and api-gateway."
            else:
                mock_response = "The auth-svc is throwing 5xx errors. We should check the logs and restart the auth service."
        
        return {
            "response": mock_response,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "latency_ms": latency_ms,
            "model": "mock-model",
            "provider": "mock"
        }
    
    @staticmethod
    def calculate_cost(input_tokens: int, output_tokens: int, 
                      input_price_per_1k: float = None,
                      output_price_per_1k: float = None,
                      input_price_per_1m: float = 0.27, 
                      output_price_per_1m: float = 0.27) -> float:
        """
        Calculate cost in USD based on token usage
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            input_price_per_1k: Price per 1K tokens (overrides per-1M if provided)
            output_price_per_1k: Price per 1K tokens (overrides per-1M if provided)
            input_price_per_1m: Price per 1M input tokens (default: Groq pricing)
            output_price_per_1m: Price per 1M output tokens (default: Groq pricing)
            
        Returns:
            Cost in USD
        """
        if input_price_per_1k is not None:
            # Use per-1K pricing (e.g., $0.0008/1K for mixtral-8x7b)
            input_cost = (input_tokens / 1_000) * input_price_per_1k
            output_cost = (output_tokens / 1_000) * (output_price_per_1k or input_price_per_1k)
        else:
            # Use per-1M pricing
            input_cost = (input_tokens / 1_000_000) * input_price_per_1m
            output_cost = (output_tokens / 1_000_000) * output_price_per_1m
        
        return input_cost + output_cost


if __name__ == "__main__":
    client = GroqClient()
    
    test_prompt = "What is the root cause of high error rates in auth-svc?"
    
    try:
        result = client.call_llm_with_fallback(test_prompt)
        print(f"Provider: {result['provider']}")
        print(f"Response: {result['response'][:100]}...")
        print(f"Tokens: {result['total_tokens']}")
        print(f"Latency: {result['latency_ms']}ms")
    except AllProvidersExhausted as e:
        print(f"All providers failed: {e}")
