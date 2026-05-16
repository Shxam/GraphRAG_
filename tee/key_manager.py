"""
Key Manager for TEE (Trusted Execution Environment)
Handles encryption key derivation and data encryption/decryption
"""

import hashlib
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class KeyManager:
    """Manages encryption keys for TEE"""
    
    @staticmethod
    def derive_sealing_key(seed: str = "postmortemiq_enclave_seed") -> bytes:
        """
        Derive a sealing key from a deterministic seed
        In production SGX, this would be derived from MRENCLAVE
        
        Args:
            seed: Seed string for key derivation
            
        Returns:
            32-byte encryption key
        """
        # Use PBKDF2HMAC to derive a key from the seed
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"postmortemiq_salt",
            iterations=100000,
        )
        key = kdf.derive(seed.encode())
        return key
    
    @staticmethod
    def encrypt_data(data: bytes, key: bytes) -> bytes:
        """
        Encrypt data using AES-256-GCM
        
        Args:
            data: Plaintext data
            key: 32-byte encryption key
            
        Returns:
            Encrypted data (nonce + ciphertext + tag)
        """
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext
    
    @staticmethod
    def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_data: Encrypted data (nonce + ciphertext + tag)
            key: 32-byte encryption key
            
        Returns:
            Plaintext data
        """
        aesgcm = AESGCM(key)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext
    
    @staticmethod
    def compute_mrenclave(code_directory: str = ".") -> str:
        """
        Compute MRENCLAVE measurement (SHA-256 hash of code)
        In production SGX, this is computed by hardware
        
        Args:
            code_directory: Directory containing application code
            
        Returns:
            Hex string of MRENCLAVE measurement
        """
        hasher = hashlib.sha256()
        
        # Hash all Python files in the directory
        for root, dirs, files in os.walk(code_directory):
            # Skip virtual environments and cache
            dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', '.git']]
            
            for file in sorted(files):
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'rb') as f:
                            hasher.update(f.read())
                    except Exception:
                        pass
        
        return hasher.hexdigest()


if __name__ == "__main__":
    # Test key derivation and encryption
    km = KeyManager()
    
    # Derive sealing key
    key = km.derive_sealing_key()
    print(f"Derived sealing key: {key.hex()[:32]}...")
    
    # Test encryption/decryption
    test_data = b"Sensitive incident data: JWT_EXPIRY_SECONDS changed"
    encrypted = km.encrypt_data(test_data, key)
    print(f"Encrypted: {encrypted.hex()[:64]}...")
    
    decrypted = km.decrypt_data(encrypted, key)
    print(f"Decrypted: {decrypted.decode()}")
    
    # Compute MRENCLAVE
    mrenclave = km.compute_mrenclave()
    print(f"MRENCLAVE: {mrenclave}")
