"""
HuggingFace Inference API Client with timeout and warm-up handling
"""

import os
import time
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from utils.logger import log_huggingface_request
    STRUCTURED_LOGGING = True
except ImportError:
    STRUCTURED_LOGGING = False


class HuggingFaceClient:
    """Client for HuggingFace Inference API with cold start handling"""
    
    def __init__(self, api_token: str = None):
        self.api_token = api_token or os.getenv("HUGGINGFACE_API_TOKEN")
        self.api_url = "https://api-inference.huggingface.co/models"
        self.headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
    
    def call_model(self, 
                   model: str,
                   inputs: Dict[str, Any],
                   max_retries: int = 2,
                   warm_up_wait: int = 30) -> Dict[str, Any]:
        """
        Call HuggingFace Inference API with cold start handling
        
        Args:
            model: Model identifier (e.g., "mistralai/Mistral-7B-Instruct-v0.1")
            inputs: Input data for the model
            max_retries: Maximum retry attempts for cold starts
            warm_up_wait: Seconds to wait for model warm-up (default: 30s)
            
        Returns:
            Model response
        """
        url = f"{self.api_url}/{model}"
        start_time = time.time()
        warm_up_time_ms = None
        
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=inputs,
                    timeout=60.0  # 60s total timeout
                )
                
                # Check for cold start / loading status
                if response.status_code == 503:
                    response_data = response.json()
                    if "loading" in response_data.get("error", "").lower():
                        estimated_time = response_data.get("estimated_time", warm_up_wait)
                        
                        if attempt < max_retries:
                            print(f"Model {model} is loading. Waiting {estimated_time}s for warm-up...")
                            time.sleep(estimated_time)
                            warm_up_time_ms = int(estimated_time * 1000)
                            continue
                        else:
                            raise Exception(f"Model still loading after {max_retries} retries")
                
                response.raise_for_status()
                latency_ms = int((time.time() - start_time) * 1000)
                
                result = response.json()
                
                # Log successful request
                if STRUCTURED_LOGGING:
                    log_huggingface_request(
                        model=model,
                        latency_ms=latency_ms,
                        success=True,
                        warm_up_time_ms=warm_up_time_ms
                    )
                
                return {
                    "result": result,
                    "latency_ms": latency_ms,
                    "warm_up_time_ms": warm_up_time_ms,
                    "model": model
                }
                
            except requests.exceptions.Timeout as e:
                latency_ms = int((time.time() - start_time) * 1000)
                error_msg = f"Request timeout after {latency_ms}ms"
                
                if attempt < max_retries:
                    print(f"HuggingFace API timeout (attempt {attempt + 1}/{max_retries + 1}). Retrying...")
                    time.sleep(5)
                    continue
                else:
                    # Log failed request
                    if STRUCTURED_LOGGING:
                        log_huggingface_request(
                            model=model,
                            latency_ms=latency_ms,
                            success=False,
                            error=error_msg
                        )
                    raise Exception(error_msg)
            
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                error_msg = str(e)
                
                # Log failed request
                if STRUCTURED_LOGGING:
                    log_huggingface_request(
                        model=model,
                        latency_ms=latency_ms,
                        success=False,
                        error=error_msg
                    )
                
                raise
    
    def call_llm_judge(self, 
                      question: str,
                      predicted_answer: str,
                      ground_truth: str,
                      model: str = "mistralai/Mistral-7B-Instruct-v0.1") -> Dict[str, Any]:
        """
        Use LLM as a judge to evaluate answer quality
        
        Args:
            question: The question asked
            predicted_answer: The predicted answer
            ground_truth: The ground truth answer
            model: Judge model to use
            
        Returns:
            Judgment result with pass/fail
        """
        prompt = f"""You are an expert evaluator. Compare the predicted answer to the ground truth answer for the given question.

Question: {question}

Ground Truth Answer: {ground_truth}

Predicted Answer: {predicted_answer}

Does the predicted answer correctly identify the same root cause as the ground truth? Answer with PASS or FAIL only.

Judgment:"""
        
        inputs = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 10,
                "temperature": 0.1,
                "return_full_text": False
            }
        }
        
        result = self.call_model(model, inputs)
        
        # Parse judgment
        judgment_text = result["result"][0].get("generated_text", "").strip().upper()
        passed = "PASS" in judgment_text
        
        return {
            "passed": passed,
            "judgment": judgment_text,
            "latency_ms": result["latency_ms"],
            "warm_up_time_ms": result.get("warm_up_time_ms")
        }


if __name__ == "__main__":
    # Test HuggingFace client
    client = HuggingFaceClient()
    
    try:
        result = client.call_llm_judge(
            question="What caused the incident?",
            predicted_answer="JWT_EXPIRY config change from 3600 to 60 seconds",
            ground_truth="Configuration change to JWT_EXPIRY_SECONDS",
            model="mistralai/Mistral-7B-Instruct-v0.1"
        )
        
        print(f"Judgment: {result['judgment']}")
        print(f"Passed: {result['passed']}")
        print(f"Latency: {result['latency_ms']}ms")
        if result.get('warm_up_time_ms'):
            print(f"Warm-up time: {result['warm_up_time_ms']}ms")
    except Exception as e:
        print(f"Error: {e}")
