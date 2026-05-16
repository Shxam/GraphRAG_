"""
PostMortemIQ - Main Entry Point
GraphRAG Incident Root-Cause Engine with Trusted Execution Environment
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestration.router import app

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ===========================================================
                         PostMortemIQ
          GraphRAG Incident Root-Cause Engine with TEE
    ===========================================================
    
    Starting API server on http://localhost:8000
    
    Endpoints:
      - GET  /           : API information
      - GET  /health     : Health check
      - GET  /attest     : TEE attestation report
      - POST /incident   : Analyze incident
      - GET  /benchmark  : Run full benchmark
    
    Dashboard: Run 'streamlit run evaluation/dashboard.py'
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
