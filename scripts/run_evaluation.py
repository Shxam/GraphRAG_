"""
Batch Evaluation Script for PostMortemIQ
Runs LLM-as-a-Judge and BERTScore evaluation on all test cases
Runs pipelines DIRECTLY (in-process) — no server needed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict

from llm.groq_client import GroqClient
from evaluation.accuracy_eval import llm_judge, compute_bertscore


def load_ground_truth(path: str = "evaluation/ground_truth.json") -> List[Dict[str, Any]]:
    """Load ground truth test cases"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_evaluation(dry_run: bool = False) -> Dict[str, Any]:
    """
    Run batch evaluation on all test cases using in-process pipeline execution.
    No server needed — pipelines run directly.
    """
    print("=" * 80)
    print("PostMortemIQ Batch Evaluation")
    print("=" * 80)
    print()

    # Load ground truth
    print("Loading ground truth test cases...")
    ground_truth_cases = load_ground_truth()

    if dry_run:
        print("DRY RUN MODE: Testing with first 3 cases only")
        ground_truth_cases = ground_truth_cases[:3]

    print(f"Loaded {len(ground_truth_cases)} test cases")
    print()

    # Initialize pipelines directly (no HTTP)
    print("Initializing pipelines...")
    from pipelines.baseline import BaselinePipeline
    from pipelines.graphrag import GraphRAGPipeline
    from pipelines.llm_only import LLMOnlyPipeline

    baseline_pipeline = BaselinePipeline()
    graphrag_pipeline = GraphRAGPipeline()
    llm_only_pipeline = LLMOnlyPipeline()

    # BasicRAG needs sentence-transformers; wrap in try/except
    basic_rag_pipeline = None
    try:
        from pipelines.basic_rag import BasicRAGPipeline
        basic_rag_pipeline = BasicRAGPipeline()
    except Exception as e:
        print(f"  Warning: BasicRAG unavailable ({e}), skipping")

    print("  [OK] Pipelines ready")
    print()

    # Initialize Groq client for LLM-as-a-Judge
    print("Initializing Groq client for LLM-as-a-Judge...")
    groq_client = GroqClient()
    if not groq_client.client:
        print("  WARNING: Groq client not initialized. Keyword fallback will be used.")
    else:
        print("  [OK] Groq client ready")
    print()

    # Storage for results
    pipeline_results = {
        "graphrag": {"predictions": [], "references": [], "scores": []},
        "basic_rag": {"predictions": [], "references": [], "scores": []},
        "llm_only": {"predictions": [], "references": [], "scores": []},
        "baseline": {"predictions": [], "references": [], "scores": []}
    }

    # Run evaluation for each test case
    print("Running evaluation on test cases...")
    print("-" * 80)

    for i, test_case in enumerate(ground_truth_cases, 1):
        incident_id = test_case["incident_id"]
        alert = test_case["alert"]
        ground_truth_summary = test_case["ground_truth_summary"]

        print(f"[{i}/{len(ground_truth_cases)}] {incident_id}: {alert['alert_name']}")

        # Build incident data
        incident_data = {
            "incident_id": incident_id,
            "alert_id": f"alert_{incident_id.split('_')[1] if '_' in incident_id else (incident_id.split('-')[1] if '-' in incident_id else '1')}",
            "alert_name": alert["alert_name"],
            "severity": alert["severity"],
            "start_time": "2024-01-15T14:33:00Z"
        }

        alert_str = f"{alert['alert_name']} (severity: {alert['severity']})"

        # Run each pipeline with error handling
        pipeline_runs = {}

        # GraphRAG
        try:
            pipeline_runs["graphrag"] = graphrag_pipeline.run(incident_id, incident_data)
        except Exception as e:
            print(f"  [!] graphrag error: {e}")
            pipeline_runs["graphrag"] = {"rca_report": f"Error: {e}"}

        # Baseline
        try:
            pipeline_runs["baseline"] = baseline_pipeline.run(incident_id, incident_data)
        except Exception as e:
            print(f"  [!] baseline error: {e}")
            pipeline_runs["baseline"] = {"rca_report": f"Error: {e}"}

        # LLM Only
        try:
            pipeline_runs["llm_only"] = llm_only_pipeline.run(incident_id, incident_data)
        except Exception as e:
            print(f"  [!] llm_only error: {e}")
            pipeline_runs["llm_only"] = {"rca_report": f"Error: {e}"}

        # Basic RAG
        if basic_rag_pipeline:
            try:
                pipeline_runs["basic_rag"] = basic_rag_pipeline.run(incident_id, incident_data)
            except Exception as e:
                print(f"  [!] basic_rag error: {e}")
                pipeline_runs["basic_rag"] = {"rca_report": f"Error: {e}"}

        # Add delay between incidents to respect API rate limits
        time.sleep(3)

        # Evaluate each pipeline
        for pipeline_name, pipeline_result in pipeline_runs.items():
            time.sleep(2)  # Delay to prevent judge rate limiting
            rca_report = pipeline_result.get("rca_report", "")

            if not rca_report or rca_report.startswith("Error:"):
                print(f"  [X] {pipeline_name}: No RCA report")
                continue

            # Run LLM-as-a-Judge (with keyword fallback on rate limit)
            judge_result = llm_judge(
                alert_str=alert_str,
                ground_truth_summary=ground_truth_summary,
                rca_report=rca_report,
                groq_client=groq_client
            )

            # Store results
            pipeline_results[pipeline_name]["predictions"].append(rca_report)
            pipeline_results[pipeline_name]["references"].append(ground_truth_summary)
            pipeline_results[pipeline_name]["scores"].append(judge_result["score"])

            verdict_symbol = "[OK]" if judge_result["verdict"] == "PASS" else "[X]"
            fallback_note = " (fallback)" if judge_result.get("raw_response", "").endswith("(fallback)") else ""
            print(f"  {verdict_symbol} {pipeline_name}: {judge_result['verdict']}{fallback_note}")

        print()

    print("-" * 80)
    print()

    # Compute aggregate metrics
    print("Computing aggregate metrics...")
    print()

    results = {
        "run_timestamp": datetime.now().isoformat(),
        "total_cases": len(ground_truth_cases),
        "dry_run": dry_run
    }

    for pipeline_name, data in pipeline_results.items():
        if not data["scores"]:
            print(f"  [!] {pipeline_name}: No results")
            results[pipeline_name] = {
                "llm_judge_pass_rate": 0.0,
                "bertscore_f1_raw": 0.0,
                "bertscore_f1_rescaled": 0.0,
                "bertscore_precision": 0.0,
                "bertscore_recall": 0.0,
                "total_evaluated": 0
            }
            continue

        # LLM-as-a-Judge pass rate
        pass_rate = sum(data["scores"]) / len(data["scores"])

        # BERTScore
        bertscore_result = compute_bertscore(
            predictions=data["predictions"],
            references=data["references"]
        )

        results[pipeline_name] = {
            "llm_judge_pass_rate": round(pass_rate, 4),
            "bertscore_f1_raw": bertscore_result["f1_raw"],
            "bertscore_f1_rescaled": bertscore_result["f1_rescaled"],
            "bertscore_precision": bertscore_result["precision"],
            "bertscore_recall": bertscore_result["recall"],
            "total_evaluated": len(data["scores"])
        }

        print(f"{pipeline_name}:")
        print(f"  LLM-Judge Pass Rate: {pass_rate:.1%}")
        print(f"  BERTScore F1 (raw): {bertscore_result['f1_raw']:.4f}")
        print(f"  BERTScore F1 (rescaled): {bertscore_result['f1_rescaled']:.4f}")
        print(f"  Cases evaluated: {len(data['scores'])}")
        print()

    # Save results
    output_path = "evaluation/results.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"  [OK] Results saved to {output_path}")
    print()

    # Print summary table
    print("=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print()
    print(f"{'Pipeline':<15} {'Pass Rate':<12} {'F1 Raw':<10} {'F1 Rescaled':<12} {'Cases':<8}")
    print("-" * 80)

    for pipeline_name in ["graphrag", "basic_rag", "llm_only", "baseline"]:
        if pipeline_name in results and isinstance(results[pipeline_name], dict):
            data = results[pipeline_name]
            print(f"{pipeline_name:<15} "
                  f"{data['llm_judge_pass_rate']:<12.1%} "
                  f"{data['bertscore_f1_raw']:<10.4f} "
                  f"{data['bertscore_f1_rescaled']:<12.4f} "
                  f"{data['total_evaluated']:<8}")

    print()
    print("=" * 80)

    # Check if targets met
    graphrag_data = results.get("graphrag", {})
    pass_rate = graphrag_data.get("llm_judge_pass_rate", 0)
    f1_rescaled = graphrag_data.get("bertscore_f1_rescaled", 0)

    print()
    print("TARGET ACHIEVEMENT:")
    pass_symbol = "[OK] PASS" if pass_rate >= 0.90 else "[X] FAIL"
    f1_symbol = "[OK] PASS" if f1_rescaled >= 0.55 else "[X] FAIL"
    print(f"  LLM-Judge >=90%: {pass_symbol} ({pass_rate:.1%})")
    print(f"  BERTScore F1 >=0.55: {f1_symbol} ({f1_rescaled:.4f})")
    print()

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run batch evaluation for PostMortemIQ")
    parser.add_argument("--dry-run", action="store_true", help="Run on first 3 cases only")

    args = parser.parse_args()

    try:
        results = run_evaluation(dry_run=args.dry_run)

        if results:
            print("[OK] Evaluation complete!")
        else:
            print("[X] Evaluation failed")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] Evaluation error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
