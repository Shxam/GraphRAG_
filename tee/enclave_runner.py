"""
Enclave Runner for TEE
Manages enclave lifecycle and data encryption/decryption
"""

import json
from typing import Dict, Any
from tee.key_manager import KeyManager
from tee.attestation import AttestationService


class EnclaveRunner:
    """Manages TEE enclave operations"""
    
    def __init__(self):
        self.key_manager = KeyManager()
        self.attestation_service = AttestationService()
        self.sealing_key = None
        self.enclave_active = False
    
    def startup_checks(self) -> bool:
        """
        Perform enclave startup checks
        
        Returns:
            True if startup successful
        """
        print("PostMortemIQ TEE Enclave starting...")
        
        # Generate attestation
        self.attestation_service.generate_mrenclave()
        print(f"[OK] MRENCLAVE generated: {self.attestation_service.mrenclave[:16]}...")
        
        # Derive sealing key
        self.sealing_key = self.key_manager.derive_sealing_key()
        print(f"[OK] Sealing key derived")
        
        # Mark enclave as active
        self.enclave_active = True
        print(f"[OK] Enclave active (simulation mode)")
        
        return True
    
    def decrypt_incident_payload(self, encrypted_payload: bytes) -> Dict[str, Any]:
        """
        Decrypt incident payload inside enclave
        
        Args:
            encrypted_payload: Encrypted incident data
            
        Returns:
            Decrypted incident dictionary
        """
        if not self.enclave_active:
            raise RuntimeError("Enclave not active")
        
        if not self.sealing_key:
            raise RuntimeError("Sealing key not available")
        
        # Decrypt
        plaintext = self.key_manager.decrypt_data(encrypted_payload, self.sealing_key)
        
        # Parse JSON
        incident_data = json.loads(plaintext.decode())
        
        return incident_data
    
    def encrypt_result(self, result_dict: Dict[str, Any]) -> bytes:
        """
        Encrypt result before leaving enclave
        
        Args:
            result_dict: Result dictionary
            
        Returns:
            Encrypted result bytes
        """
        if not self.enclave_active:
            raise RuntimeError("Enclave not active")
        
        if not self.sealing_key:
            raise RuntimeError("Sealing key not available")
        
        # Serialize to JSON
        plaintext = json.dumps(result_dict).encode()
        
        # Encrypt
        encrypted = self.key_manager.encrypt_data(plaintext, self.sealing_key)
        
        return encrypted
    
    def get_attestation_report(self) -> Dict[str, Any]:
        """Get current attestation report"""
        return self.attestation_service.generate_attestation_report()
    
    def get_status(self) -> Dict[str, Any]:
        """Get enclave status"""
        return {
            "enclave_active": self.enclave_active,
            "sealing_key_loaded": self.sealing_key is not None,
            **self.attestation_service.get_enclave_status()
        }
    
    def shutdown(self):
        """Shutdown enclave and clear keys"""
        print("Shutting down enclave...")
        self.sealing_key = None
        self.enclave_active = False
        print("[OK] Enclave shutdown complete")


if __name__ == "__main__":
    runner = EnclaveRunner()
    
    # Startup
    runner.startup_checks()
    
    # Test encryption/decryption
    test_incident = {
        "incident_id": "incident_1",
        "alert_name": "High error rate",
        "severity": "critical"
    }
    
    print("\nTesting incident encryption...")
    encrypted = runner.encrypt_result(test_incident)
    print(f"Encrypted: {encrypted.hex()[:64]}...")
    
    print("\nTesting incident decryption...")
    decrypted = runner.decrypt_incident_payload(encrypted)
    print(f"Decrypted: {decrypted}")
    
    # Get status
    print("\nEnclave status:")
    print(json.dumps(runner.get_status(), indent=2))
    
    # Shutdown
    runner.shutdown()
