"""
Alert Deduplication Module
Prevents duplicate alerts from being processed within a time window
"""

import hashlib
import time
from typing import Dict, Any, Optional
from datetime import datetime


class AlertDeduplicator:
    """Deduplicates alerts based on fingerprint within a time window"""
    
    def __init__(self, window_seconds: int = 300):
        """
        Initialize the deduplicator
        
        Args:
            window_seconds: Time window for deduplication (default 300 seconds)
        """
        self.window_seconds = window_seconds
        self.seen_fingerprints: Dict[str, float] = {}
        self.total_seen = 0
        self.duplicates_blocked = 0
    
    def generate_fingerprint(self, alert: Dict[str, Any]) -> str:
        """
        Generate MD5 fingerprint from alert attributes
        
        Args:
            alert: Alert dictionary with service, error_type, component
            
        Returns:
            MD5 hash string
        """
        # Extract key fields for fingerprinting
        service = alert.get("service", alert.get("alert_name", "unknown"))
        error_type = alert.get("error_type", alert.get("severity", "unknown"))
        component = alert.get("component", alert.get("alert_id", "unknown"))
        
        # Create fingerprint string
        fingerprint_str = f"{service}:{error_type}:{component}"
        
        # Generate MD5 hash
        return hashlib.md5(fingerprint_str.encode()).hexdigest()
    
    def is_duplicate(self, alert: Dict[str, Any]) -> bool:
        """
        Check if alert is a duplicate within the time window
        
        Args:
            alert: Alert dictionary
            
        Returns:
            True if duplicate, False if new or outside window
        """
        self.total_seen += 1
        
        fingerprint = self.generate_fingerprint(alert)
        current_time = time.time()
        
        # Clean up old fingerprints outside the window
        self._cleanup_old_fingerprints(current_time)
        
        # Check if we've seen this fingerprint recently
        if fingerprint in self.seen_fingerprints:
            first_seen = self.seen_fingerprints[fingerprint]
            time_diff = current_time - first_seen
            
            if time_diff <= self.window_seconds:
                self.duplicates_blocked += 1
                return True
        
        # Record this fingerprint
        self.seen_fingerprints[fingerprint] = current_time
        return False
    
    def _cleanup_old_fingerprints(self, current_time: float):
        """Remove fingerprints outside the time window"""
        expired = [
            fp for fp, timestamp in self.seen_fingerprints.items()
            if current_time - timestamp > self.window_seconds
        ]
        for fp in expired:
            del self.seen_fingerprints[fp]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get deduplication statistics
        
        Returns:
            Dictionary with total_seen, duplicates_blocked, dedup_rate_pct
        """
        dedup_rate = (
            (self.duplicates_blocked / self.total_seen * 100)
            if self.total_seen > 0
            else 0.0
        )
        
        return {
            "total_seen": self.total_seen,
            "duplicates_blocked": self.duplicates_blocked,
            "dedup_rate_pct": round(dedup_rate, 2)
        }


if __name__ == "__main__":
    # Test the deduplicator
    dedup = AlertDeduplicator(window_seconds=300)
    
    # Test alert
    alert1 = {
        "service": "auth-svc",
        "error_type": "high_error_rate",
        "component": "jwt_validator"
    }
    
    alert2 = {
        "service": "auth-svc",
        "error_type": "high_error_rate",
        "component": "jwt_validator"
    }
    
    alert3 = {
        "service": "payment-svc",
        "error_type": "timeout",
        "component": "stripe_client"
    }
    
    print(f"Alert 1 is duplicate: {dedup.is_duplicate(alert1)}")  # False
    print(f"Alert 2 is duplicate: {dedup.is_duplicate(alert2)}")  # True
    print(f"Alert 3 is duplicate: {dedup.is_duplicate(alert3)}")  # False
    
    print(f"\nStats: {dedup.get_stats()}")
