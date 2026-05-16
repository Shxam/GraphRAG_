"""
Attestation Service for TEE
Generates and verifies attestation reports
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any
from tee.key_manager import KeyManager


class AttestationService:
    """Handles TEE attestation"""
    
    def __init__(self):
        self.key_manager = KeyManager()
        self.mrenclave = None
        self.attestation_timestamp = None
    
    def generate_mrenclave(self, code_directory: str = ".") -> str:
        """
        Generate MRENCLAVE measurement
        
        Args:
            code_directory: Directory to measure
            
        Returns:
            MRENCLAVE hash
        """
        self.mrenclave = self.key_manager.compute_mrenclave(code_directory)
        self.attestation_timestamp = datetime.now(timezone.utc).isoformat()
        return self.mrenclave
    
    def generate_attestation_report(self) -> Dict[str, Any]:
        """
        Generate attestation report
        
        Returns:
            Attestation report with MRENCLAVE and metadata
        """
        if not self.mrenclave:
            self.generate_mrenclave()
        
        return {
            "mrenclave": self.mrenclave,
            "timestamp": self.attestation_timestamp,
            "status": "verified",
            "mode": "simulation",
            "platform": "Gramine-SGX",
            "version": "1.0.0",
            "tcb_level": "simulation"
        }
    
    def verify_attestation(self, report: Dict[str, Any], expected_mrenclave: str = None) -> bool:
        """
        Verify attestation report
        
        Args:
            report: Attestation report to verify
            expected_mrenclave: Expected MRENCLAVE value (optional)
            
        Returns:
            True if attestation is valid
        """
        # Check required fields
        if not all(k in report for k in ["mrenclave", "timestamp", "status"]):
            return False
        
        # Check status
        if report["status"] != "verified":
            return False
        
        # Check MRENCLAVE if provided
        if expected_mrenclave and report["mrenclave"] != expected_mrenclave:
            return False
        
        return True
    
    def get_enclave_status(self) -> Dict[str, Any]:
        """
        Get current enclave status
        
        Returns:
            Enclave status information
        """
        return {
            "active": True,
            "mode": "simulation",
            "mrenclave": self.mrenclave[:16] + "..." if self.mrenclave else "not_generated",
            "last_attestation": self.attestation_timestamp,
            "platform": "Gramine-SGX (simulation mode)"
        }


if __name__ == "__main__":
    service = AttestationService()
    
    # Generate attestation
    print("Generating attestation report...")
    report = service.generate_attestation_report()
    print(f"MRENCLAVE: {report['mrenclave']}")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Status: {report['status']}")
    
    # Verify attestation
    is_valid = service.verify_attestation(report)
    print(f"\nAttestation valid: {is_valid}")
    
    # Get enclave status
    status = service.get_enclave_status()
    print(f"\nEnclave status: {json.dumps(status, indent=2)}")
