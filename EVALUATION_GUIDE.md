# PostMortemIQ Evaluation Guide

Quick guide for running accuracy evaluation and viewing results.

---

## Prerequisites

```bash
# Install dependencies (if not already done)
make install

# Ensure you have API keys configured
cp .env.example .env
# Edit .env and add:
# - GROQ_API_KEY (required)
# - HUGGINGFACE_API_TOKEN (required for LLM-as-a-Judge)
# - OPENAI_API_KEY (optional, for embeddings)
```

---

## Quick Start

### 1. Generate Evaluation Questions

```bash
python evaluation/accuracy_eval.py --generate-questions
```

This creates `data/eval_questions.json` with 20 test questions across 4 difficulty tiers:
- **Easy (5):** Single-service incidents
- **Medium (5):** Cascading failures
- **Hard (5):** Multi-team config changes
- **Adversarial (5):** Ambiguous or insufficient data

### 2. Run Full Evaluation

```bash
make eval
# Or: python evaluation/accuracy_eval.py
```

This will:
1. Load evaluation questions
2. Run all 3 pipelines (Baseline, GraphRAG, LLM-Only) on each question
3. Evaluate using LLM-as-a-Judge (Mistral-7B)
4. Calculate BERTScore (distilbert-base-uncased)
5. Generate results and report

**Expected Duration:** 5-10 minutes (20 questions × 3 pipelines = 60 API calls)

### 3. View Results

```bash
# View JSON results
cat data/benchmark_results.json | python -m json.tool

# View markdown report
cat evaluation/eval_report.md

# View in dashboard
make dashboard
# Navigate to "Benchmark Dashboard" tab
```

---

## Evaluation Methods

### Method A: LLM-as-a-Judge

**Model:** Mistral-7B-Instruct (via HuggingFace Inference API)

**Process:**
1. For each question, compare system response to ground truth
2. LLM judge evaluates: factual accuracy, completeness, hallucinations
3. Returns: PASS/FAIL verdict + reasoning + confidence score

**Target:** ≥90% pass rate

**Example:**
```json
{
  "question": "What caused the API gateway timeout?",
  "ground_truth": "Load balancer timeout misconfigured to 1s instead of 30s",
  "response": "The timeout was set to 1 second causing requests to fail",
  "verdict": "PASS",
  "reasoning": "Response correctly identifies the timeout misconfiguration",
  "confidence": 0.95
}
```

### Method B: BERTScore

**Model:** distilbert-base-uncased

**Process:**
1. Compute token-level semantic similarity between response and ground truth
2. Calculate precision, recall, and F1 score
3. Rescale F1 from [0.5, 1.0] to [0.0, 1.0] for interpretability

**Target:** ≥0.55 F1 (rescaled)

**Metrics:**
- **Precision:** How much of the response is relevant
- **Recall:** How much of the ground truth is covered
- **F1:** Harmonic mean of precision and recall

---

## Understanding Results

### Overall Summary

```json
{
  "summary": {
    "baseline_pass_rate": 0.85,
    "graphrag_pass_rate": 0.92,
    "llm_only_pass_rate": 0.62,
    "graphrag_meets_target": true,
    "graphrag_bertscore_f1": 0.58,
    "graphrag_bertscore_meets_target": true
  }
}
```

**Interpretation:**
- ✅ GraphRAG achieves 92% pass rate (target: ≥90%)
- ✅ GraphRAG achieves 0.58 BERTScore F1 (target: ≥0.55)
- 📈 GraphRAG outperforms Baseline by 7%
- 📈 GraphRAG outperforms LLM-Only by 30%

### Difficulty Breakdown

```json
{
  "difficulty_breakdown": {
    "easy": {"pass_rate": 1.0, "count": 5},
    "medium": {"pass_rate": 0.9, "count": 5},
    "hard": {"pass_rate": 0.85, "count": 5},
    "adversarial": {"pass_rate": 0.9, "count": 5}
  }
}
```

**Interpretation:**
- **Easy:** 100% pass rate (5/5) - Single-service incidents
- **Medium:** 90% pass rate (4.5/5) - Cascading failures
- **Hard:** 85% pass rate (4.25/5) - Multi-team config changes
- **Adversarial:** 90% pass rate (4.5/5) - Correctly handles insufficient data

### Individual Results

```json
{
  "individual_results": [
    {
      "question_id": "eval_001",
      "difficulty": "easy",
      "category": "root_cause",
      "pass": true,
      "reasoning": "Correctly identifies timeout misconfiguration",
      "confidence": 0.95,
      "response": "The load balancer timeout was set to 1 second..."
    }
  ]
}
```

---

## Troubleshooting

### Issue: Rate Limit Errors

**Symptom:** `RateLimitError: Too many requests`

**Solution:**
```bash
# Wait a few minutes and retry
# Or reduce concurrent requests by running evaluation in batches
```

**Prevention:**
- Groq free tier: 14,400 requests/day
- 3 pipelines × 20 questions = 60 requests minimum
- With retries: ~100-150 requests total
- Stay well below daily limit

### Issue: HuggingFace Cold Start

**Symptom:** `Model is loading, please wait...`

**Solution:**
- Evaluation automatically waits 30s for model warm-up
- No action needed, just be patient

**Note:** First request to HuggingFace may take 20-30s

### Issue: BERTScore Installation

**Symptom:** `ModuleNotFoundError: No module named 'bert_score'`

**Solution:**
```bash
pip install bert-score==0.3.13
```

### Issue: Missing Evaluation Questions

**Symptom:** `FileNotFoundError: data/eval_questions.json not found`

**Solution:**
```bash
python evaluation/accuracy_eval.py --generate-questions
```

---

## Advanced Usage

### Custom Evaluation Questions

Edit `data/eval_questions.json`:

```json
{
  "id": "custom_001",
  "difficulty": "medium",
  "question": "Your custom question here",
  "ground_truth": "Expected answer here",
  "incident_id": "incident_1",
  "category": "root_cause"
}
```

### Evaluate Single Pipeline

```python
from evaluation.accuracy_eval import AccuracyEvaluator

evaluator = AccuracyEvaluator()
questions = evaluator.load_eval_questions()

# Evaluate only GraphRAG
graphrag_results = await evaluator.evaluate_pipeline(
    evaluator.graphrag_pipeline,
    'graphrag',
    questions
)
```

### Cache Management

Evaluation caches LLM-Judge responses to avoid redundant API calls:

```bash
# View cache
ls -lh data/.eval_cache/

# Clear cache (forces re-evaluation)
rm -rf data/.eval_cache/
```

---

## Interpreting Adversarial Results

Adversarial questions test whether the system correctly identifies insufficient data:

**Example:**
```
Question: "Which team was responsible for the API gateway timeout?"
Ground Truth: "Insufficient data - not specified in incident report"
```

**Good Response (PASS):**
> "The incident report does not specify which team made the configuration change."

**Bad Response (FAIL):**
> "The Platform Team was responsible for the timeout." (hallucination)

**Why This Matters:**
- In production, saying "I don't know" is better than hallucinating
- Adversarial handling prevents false confidence
- Critical for safety-critical systems

---

## Performance Optimization

### Parallel Evaluation

Evaluation runs pipelines in parallel using `asyncio.gather()`:

```python
# All 3 pipelines run simultaneously
baseline, graphrag, llm_only = await asyncio.gather(
    baseline_pipeline.analyze(incident_id),
    graphrag_pipeline.analyze(incident_id),
    llm_only_pipeline.analyze(incident_id)
)
```

**Speedup:** 3x faster than sequential execution

### Response Caching

LLM-Judge responses are cached by hash:

```python
cache_key = f"{hash(question)}_{hash(ground_truth)}_{hash(response)}"
cache_path = f"data/.eval_cache/judge_{cache_key}.json"
```

**Benefit:** Re-running evaluation on same questions is instant

---

## Cost Estimation

### API Costs

**Per Evaluation Run (20 questions):**
- Groq (3 pipelines × 20 questions): ~$0.10
- HuggingFace (LLM-Judge, 20 questions): Free (with API token)
- BERTScore: Free (local computation)

**Total:** ~$0.10 per full evaluation

**Monthly (daily evaluation):**
- 30 runs × $0.10 = $3.00/month

---

## Next Steps

After running evaluation:

1. **View Dashboard**
   ```bash
   make dashboard
   # Navigate to "Benchmark Dashboard" tab
   ```

2. **Analyze Results**
   - Check pass rates by difficulty
   - Review failed questions
   - Examine BERTScore metrics

3. **Tune Parameters** (if needed)
   - Adjust retrieval settings in `configs/server_config.json`
   - Modify chunking parameters
   - Update entity extraction prompts

4. **Re-evaluate**
   ```bash
   make eval
   ```

---

## References

- **LLM-as-a-Judge:** [Paper](https://arxiv.org/abs/2306.05685)
- **BERTScore:** [Paper](https://arxiv.org/abs/1904.09675) | [GitHub](https://github.com/Tiiiger/bert_score)
- **TigerGraph GraphRAG:** [Docs](https://github.com/tigergraph/graphrag)

---

## Support

**Issues?** Open a GitHub issue or check:
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [FAQ.md](FAQ.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

**Questions?** See [PROJECT_DEEP_DIVE.md](PROJECT_DEEP_DIVE.md) for architecture details.

---

**Happy Evaluating! 🎯**
