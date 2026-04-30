"""
Groq API Client for PostMortemIQ
Handles LLM inference calls with token tracking and multi-provider fallback
"""

import os
import time
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

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
        
        if GROQ_AVAILABLE and self.api_key:
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None
    
    def call_llm(self, prompt: str, model: str = "mixtral-8x7b-32768") -> Dict[str, Any]:
        """
        Call Groq LLM API and track metrics
        
        Args:
            prompt: The prompt to send
            model: Model identifier
            
        Returns:
            Dictionary with response, tokens, and latency
        """
        start_time = time.time()
        
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=model,
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
                    "model": model,
                    "provider": "groq"
                }
            except Exception as e:
                print(f"Groq API error: {e}")
                return self._mock_response(prompt, start_time)
        else:
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
        
        # Try Groq first
        try:
            result = self._call_groq(prompt)
            return result
        except Exception as e:
            error_msg = str(e)
            providers_tried.append(("Groq", error_msg))
            print(f"Groq failed: {error_msg}")
        
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
        time.sleep(0.5)  # Simulate API latency
        
        input_tokens = len(prompt) // 4  # Rough estimate
        output_tokens = 150
        latency_ms = int((time.time() - start_time) * 1000)
        
        mock_response = """Root Cause Analysis:

The incident was caused by a configuration change to JWT_EXPIRY_SECONDS from 3600 to 60 seconds
in deployment v2.4.1 of the auth-svc service. This change caused authentication tokens to expire
much faster than expected, leading to cascading failures in downstream services.

Affected Services:
- auth-svc (primary)
- payment-svc (dependent)
- api-gateway (dependent)

Teams to Page:
- Payments team (owns payment-svc)
- API team (owns api-gateway)

Recommended Remediation:
1. Rollback JWT_EXPIRY_SECONDS to 3600
2. Deploy hotfix to auth-svc
3. Monitor token validation metrics
4. Page affected teams for awareness"""
        
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
                      input_price_per_1m: float = 0.27, 
                      output_price_per_1m: float = 0.27) -> float:
        """
        Calculate cost in USD based on token usage
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            input_price_per_1m: Price per 1M input tokens
            output_price_per_1m: Price per 1M output tokens
            
        Returns:
            Cost in USD
        """
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
