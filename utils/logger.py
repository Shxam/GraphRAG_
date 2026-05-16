"""
Structured JSON Logger for PostMortemIQ
Logs pipeline execution with timestamps, tokens, latency, errors
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import threading

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Thread-local storage for request context
_context = threading.local()


class StructuredLogger:
    """Structured JSON logger with Groq API request tracking"""
    
    def __init__(self, log_level: str = None):
        self.log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
        self.log_file = LOGS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        # Groq API request counter (thread-safe)
        self._groq_requests_made = 0
        self._groq_requests_limit = 14400  # Free tier daily limit
        self._lock = threading.Lock()
        
        # Configure Python logging
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("postmortemiq")
    
    def log_pipeline_execution(self, 
                              pipeline: str,
                              incident_id: str,
                              tokens: int,
                              latency_ms: int,
                              cost_usd: float,
                              success: bool = True,
                              error: Optional[str] = None,
                              **kwargs) -> None:
        """
        Log pipeline execution with structured data
        
        Args:
            pipeline: Pipeline name (baseline, graphrag, llm_only)
            incident_id: Incident identifier
            tokens: Total tokens used
            latency_ms: Execution latency in milliseconds
            cost_usd: Cost in USD
            success: Whether execution succeeded
            error: Error message if failed
            **kwargs: Additional metadata
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline": pipeline,
            "incident_id": incident_id,
            "tokens": tokens,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "success": success,
            "error": error,
            **kwargs
        }
        
        # Write to JSONL file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Also log to console
        if success:
            self.logger.info(f"Pipeline {pipeline} completed for {incident_id}: {tokens} tokens, {latency_ms}ms, ${cost_usd:.6f}")
        else:
            self.logger.error(f"Pipeline {pipeline} failed for {incident_id}: {error}")
    
    def log_groq_request(self, 
                        model: str,
                        tokens: int,
                        latency_ms: int,
                        retry_count: int = 0,
                        success: bool = True,
                        error: Optional[str] = None) -> None:
        """
        Log Groq API request and update counter
        
        Args:
            model: Model name
            tokens: Total tokens used
            latency_ms: Request latency
            retry_count: Number of retries
            success: Whether request succeeded
            error: Error message if failed
        """
        with self._lock:
            self._groq_requests_made += 1
            requests_remaining = self._groq_requests_limit - self._groq_requests_made
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "groq_api_call",
            "model": model,
            "tokens": tokens,
            "latency_ms": latency_ms,
            "retry_count": retry_count,
            "success": success,
            "error": error,
            "requests_made": self._groq_requests_made,
            "requests_remaining": requests_remaining
        }
        
        # Write to JSONL file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Warn if approaching limit
        if requests_remaining < 500:
            self.logger.warning(f"[WARN] Groq API requests remaining: {requests_remaining} (limit: {self._groq_requests_limit})")
        
        if success:
            self.logger.debug(f"Groq API call: {model}, {tokens} tokens, {latency_ms}ms (retries: {retry_count})")
        else:
            self.logger.error(f"Groq API call failed: {error}")
    
    def log_huggingface_request(self,
                                model: str,
                                latency_ms: int,
                                success: bool = True,
                                error: Optional[str] = None,
                                warm_up_time_ms: Optional[int] = None) -> None:
        """
        Log HuggingFace Inference API request
        
        Args:
            model: Model name
            latency_ms: Request latency
            success: Whether request succeeded
            error: Error message if failed
            warm_up_time_ms: Cold start warm-up time if applicable
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "huggingface_api_call",
            "model": model,
            "latency_ms": latency_ms,
            "warm_up_time_ms": warm_up_time_ms,
            "success": success,
            "error": error
        }
        
        # Write to JSONL file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        if warm_up_time_ms:
            self.logger.info(f"HuggingFace model {model} cold start: {warm_up_time_ms}ms warm-up")
        
        if success:
            self.logger.debug(f"HuggingFace API call: {model}, {latency_ms}ms")
        else:
            self.logger.error(f"HuggingFace API call failed: {error}")
    
    def log_timeout(self, 
                   pipeline: str,
                   incident_id: str,
                   timeout_ms: int,
                   elapsed_ms: int) -> None:
        """
        Log pipeline timeout
        
        Args:
            pipeline: Pipeline name
            incident_id: Incident identifier
            timeout_ms: Configured timeout
            elapsed_ms: Time elapsed before timeout
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "timeout",
            "pipeline": pipeline,
            "incident_id": incident_id,
            "timeout_ms": timeout_ms,
            "elapsed_ms": elapsed_ms
        }
        
        # Write to JSONL file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        self.logger.warning(f"[TIMEOUT] Pipeline {pipeline} timeout for {incident_id}: {elapsed_ms}ms (limit: {timeout_ms}ms)")
    
    def get_groq_requests_remaining(self) -> int:
        """Get remaining Groq API requests for the day"""
        with self._lock:
            return self._groq_requests_limit - self._groq_requests_made
    
    def reset_groq_counter(self) -> None:
        """Reset Groq request counter (call at midnight UTC)"""
        with self._lock:
            self._groq_requests_made = 0
        self.logger.info("Groq API request counter reset")


# Global logger instance
_logger_instance = None


def get_logger() -> StructuredLogger:
    """Get or create global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger()
    return _logger_instance


def log_pipeline_execution(*args, **kwargs):
    """Convenience function for logging pipeline execution"""
    get_logger().log_pipeline_execution(*args, **kwargs)


def log_groq_request(*args, **kwargs):
    """Convenience function for logging Groq API requests"""
    get_logger().log_groq_request(*args, **kwargs)


def log_huggingface_request(*args, **kwargs):
    """Convenience function for logging HuggingFace API requests"""
    get_logger().log_huggingface_request(*args, **kwargs)


def log_timeout(*args, **kwargs):
    """Convenience function for logging timeouts"""
    get_logger().log_timeout(*args, **kwargs)


def get_groq_requests_remaining() -> int:
    """Get remaining Groq API requests"""
    return get_logger().get_groq_requests_remaining()


if __name__ == "__main__":
    # Test logging
    logger = get_logger()
    
    # Test pipeline execution log
    logger.log_pipeline_execution(
        pipeline="graphrag",
        incident_id="incident_1",
        tokens=380,
        latency_ms=890,
        cost_usd=0.0003,
        success=True
    )
    
    # Test Groq API log
    logger.log_groq_request(
        model="llama-3.3-70b-versatile",
        tokens=380,
        latency_ms=740,
        retry_count=0,
        success=True
    )
    
    # Test timeout log
    logger.log_timeout(
        pipeline="baseline",
        incident_id="incident_2",
        timeout_ms=10000,
        elapsed_ms=12500
    )
    
    print(f"Groq requests remaining: {logger.get_groq_requests_remaining()}")
    print(f"Log file: {logger.log_file}")
