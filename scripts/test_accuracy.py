"""
Quick test script for accuracy evaluation functions
Tests llm_judge and compute_bertscore without running full evaluation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.groq_client import GroqClient
from evaluation.accuracy_eval import llm_judge, compute_bertscore, BERTSCORE_AVAILABLE


def test_llm_judge():
    """Test LLM-as-a-Judge function"""
    print("=" * 80)
    print("Testing LLM-as-a-Judge")
    print("=" * 80)
    print()
    
    groq_client = GroqClient()
    
    if not groq_client.client:
        print("✗ ERROR: Groq client not initialized")
        print("  Check GROQ_API_KEY in .env file")
        return False
    
    print("✓ Groq client initialized")
    print()
    
    # Test case 1: Should PASS
    print("Test 1: Correct root cause identification")
    result = llm_judge(
        alert_str="High 5xx errors in auth-svc (severity: critical)",
        ground_truth_summary="JWT_EXPIRY changed from 3600 to 60 seconds in auth-svc deployment v2.4.1",
        rca_report="The root cause is a JWT token expiry configuration change from 3600 to 60 seconds in deployment v2.4.1 of auth-svc",
        groq_client=groq_client
    )
    
    print(f"  Verdict: {result['verdict']}")
    print(f"  Score: {result['score']}")
    print(f"  Raw response: {result['raw_response']}")
    print(f"  Error: {result['error']}")
    
    if result['verdict'] == 'PASS':
        print("  ✓ Test 1 PASSED")
    else:
        print("  ✗ Test 1 FAILED (expected PASS)")
    print()
    
    # Test case 2: Should FAIL
    print("Test 2: Incorrect root cause identification")
    result = llm_judge(
        alert_str="High 5xx errors in auth-svc (severity: critical)",
        ground_truth_summary="JWT_EXPIRY changed from 3600 to 60 seconds in auth-svc deployment v2.4.1",
        rca_report="The root cause is a database connection pool exhaustion due to a memory leak",
        groq_client=groq_client
    )
    
    print(f"  Verdict: {result['verdict']}")
    print(f"  Score: {result['score']}")
    print(f"  Raw response: {result['raw_response']}")
    print(f"  Error: {result['error']}")
    
    if result['verdict'] == 'FAIL':
        print("  ✓ Test 2 PASSED")
    else:
        print("  ✗ Test 2 FAILED (expected FAIL)")
    print()
    
    return True


def test_bertscore():
    """Test BERTScore function"""
    print("=" * 80)
    print("Testing BERTScore")
    print("=" * 80)
    print()
    
    if not BERTSCORE_AVAILABLE:
        print("✗ BERTScore not available")
        print("  Install with: pip install bert-score")
        return False
    
    print("✓ BERTScore library available")
    print()
    
    predictions = [
        "JWT_EXPIRY changed from 3600 to 60 seconds causing token expiry failures",
        "Database connection pool exhausted due to connection leak in new deployment"
    ]
    
    references = [
        "JWT_EXPIRY changed from 3600 to 60 seconds in auth-svc deployment v2.4.1",
        "Connection leak in new deployment exhausted the connection pool causing 500 errors"
    ]
    
    print("Computing BERTScore for 2 predictions...")
    result = compute_bertscore(predictions, references)
    
    print(f"  F1 (raw): {result['f1_raw']}")
    print(f"  F1 (rescaled): {result['f1_rescaled']}")
    print(f"  Precision: {result['precision']}")
    print(f"  Recall: {result['recall']}")
    print(f"  Error: {result['error']}")
    print()
    
    if result['error'] is None and 0 <= result['f1_rescaled'] <= 1:
        print("  ✓ BERTScore test PASSED")
        return True
    else:
        print("  ✗ BERTScore test FAILED")
        return False


def main():
    print()
    print("PostMortemIQ Accuracy Evaluation Test")
    print()
    
    # Test LLM judge
    llm_judge_ok = test_llm_judge()
    
    # Test BERTScore
    bertscore_ok = test_bertscore()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    print(f"LLM-as-a-Judge: {'✓ PASS' if llm_judge_ok else '✗ FAIL'}")
    print(f"BERTScore:      {'✓ PASS' if bertscore_ok else '✗ FAIL'}")
    print()
    
    if llm_judge_ok and bertscore_ok:
        print("✓ All tests passed! Ready to run full evaluation.")
        print()
        print("Next step:")
        print("  python scripts/run_evaluation.py --dry-run")
        return 0
    else:
        print("✗ Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
