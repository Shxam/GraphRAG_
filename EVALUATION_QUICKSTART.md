# Accuracy Evaluation - Quick Start Guide

## 🎯 Goal
Get real LLM-as-a-Judge and BERTScore metrics for your hackathon submission.

---

## ⚡ Quick Start (5 minutes)

### Step 1: Install BERTScore
```bash
pip install bert-score
```

### Step 2: Verify Implementation
```bash
python scripts/test_accuracy.py
```

**Expected output:**
```
PostMortemIQ Accuracy Evaluation Test

Testing LLM-as-a-Judge
✓ Groq client initialized

Test 1: Correct root cause identification
  Verdict: PASS
  Score: 1.0
  ✓ Test 1 PASSED

Test 2: Incorrect root cause identification
  Verdict: FAIL
  Score: 0.0
  ✓ Test 2 PASSED

Testing BERTScore
✓ BERTScore library available
Computing BERTScore for 2 predictions...
  F1 (raw): 0.9234
  F1 (rescaled): 0.5213
  ✓ BERTScore test PASSED

TEST SUMMARY
LLM-as-a-Judge: ✓ PASS
BERTScore:      ✓ PASS

✓ All tests passed! Ready to run full evaluation.
```

### Step 3: Start API Server
```bash
python main.py
```

### Step 4: Run Dry Run (3 test cases)
```bash
# In a new terminal
python scripts/run_evaluation.py --dry-run
```

### Step 5: Run Full Evaluation (15 test cases)
```bash
python scripts/run_evaluation.py
```

---

## 📊 Understanding Results

### Results File: `evaluation/results.json`

```json
{
  "run_timestamp": "2026-05-16T12:34:56",
  "total_cases": 15,
  "graphrag": {
    "llm_judge_pass_rate": 0.9333,
    "bertscore_f1_raw": 0.9287,
    "bertscore_f1_rescaled": 0.5544,
    "bertscore_precision": 0.9301,
    "bertscore_recall": 0.9273,
    "total_evaluated": 15
  },
  "basic_rag": {
    "llm_judge_pass_rate": 0.8667,
    "bertscore_f1_raw": 0.9123,
    "bertscore_f1_rescaled": 0.4519,
    "total_evaluated": 15
  },
  "llm_only": {
    "llm_judge_pass_rate": 0.6000,
    "bertscore_f1_raw": 0.8654,
    "bertscore_f1_rescaled": 0.1588,
    "total_evaluated": 15
  },
  "baseline": {
    "llm_judge_pass_rate": 0.8000,
    "bertscore_f1_raw": 0.8891,
    "bertscore_f1_rescaled": 0.3069,
    "total_evaluated": 15
  }
}
```

### Key Metrics Explained

**LLM-as-a-Judge Pass Rate:**
- Percentage of test cases where LLM judge said "PASS"
- Target: ≥90% for bonus points
- GraphRAG should be highest

**BERTScore F1 (rescaled):**
- Semantic similarity score (0-1 scale)
- Rescaled from typical 0.84-1.0 range
- Target: ≥0.55 for bonus points
- Formula: `(f1_raw - 0.84) / (1.0 - 0.84)`

**BERTScore F1 (raw):**
- Original BERTScore F1 (typically 0.84-1.0)
- Target: ≥0.88 for bonus points

---

## 🔧 Troubleshooting

### Error: "Groq client not initialized"
**Solution:**
```bash
# Check .env file has GROQ_API_KEY
cat .env | grep GROQ_API_KEY

# If missing, add it:
echo "GROQ_API_KEY=your_key_here" >> .env
```

### Error: "BERTScore not available"
**Solution:**
```bash
pip install bert-score
```

### Error: "API timeout"
**Solution:**
- Increase timeout in `scripts/run_evaluation.py` (line with `timeout=60`)
- Or run fewer cases with `--dry-run`

### Error: "Rate limit hit"
**Solution:**
- Groq free tier: 14,400 requests/day
- Full evaluation uses: 15 cases × 4 pipelines × 2 (pipeline + judge) = 120 calls
- Wait a few minutes and retry

### Low Pass Rate (<90%)
**Solutions:**
1. Check ground truth quality in `evaluation/ground_truth.json`
2. Improve prompts in `llm/prompt_builder.py`
3. Tune GraphRAG parameters in `configs/server_config.json`:
   ```json
   {
     "top_k": 3,
     "num_hops": 2,
     "chunk_only": true
   }
   ```

### Low BERTScore (<0.55)
**Solutions:**
1. Improve RCA report quality (more specific root causes)
2. Ensure ground truth summaries are detailed
3. Check that pipelines are returning complete reports

---

## 📈 Updating BENCHMARK.md

After running full evaluation, update `BENCHMARK.md` with real numbers:

### Before:
```markdown
| **LLM-as-a-Judge pass rate** | **[TBD]%** | **[TBD]%** | **[TBD]%** | **[TBD]%** |
| **BERTScore F1 (rescaled)** | **[TBD]** | **[TBD]** | **[TBD]** | **[TBD]** |
```

### After:
```markdown
| **LLM-as-a-Judge pass rate** | **60.0%** | **86.7%** | **93.3%** ✅ | **80.0%** |
| **BERTScore F1 (rescaled)** | **0.16** | **0.45** | **0.55** ✅ | **0.31** |
```

---

## 🎯 Target Achievement

### Hackathon Judging Criteria:

**Required (30% of score):**
- ✅ Token reduction >85%
- ✅ Real accuracy evaluation (not keyword matching)

**Bonus Points:**
- ✅ LLM-as-a-Judge pass rate ≥90%
- ✅ BERTScore F1 rescaled ≥0.55

### What Judges Look For:

1. **Real evaluation** (not fake/keyword matching) ✅
2. **Reproducible** (they can run `python scripts/run_evaluation.py`) ✅
3. **Ground truth dataset** (15 test cases) ✅
4. **Multiple metrics** (LLM-Judge + BERTScore) ✅
5. **Documented methodology** (this guide) ✅

---

## 🚀 Per-Query Accuracy (Live API)

The `/analyze/sync` endpoint now returns real-time accuracy:

```bash
curl -X POST http://localhost:8000/analyze/sync \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "INC-1005",
    "alert_name": "High 5xx errors in auth-svc",
    "severity": "critical"
  }'
```

**Response includes:**
```json
{
  "graphrag_result": {
    "rca_report": "...",
    "total_tokens": 1002,
    "accuracy": 1.0,
    "llm_judge_verdict": "PASS"
  },
  "basic_rag_result": {
    "rca_report": "...",
    "total_tokens": 2134,
    "accuracy": 1.0,
    "llm_judge_verdict": "PASS"
  },
  "token_reduction_pct": 53.0
}
```

**Note:** Per-query accuracy adds 4 Groq calls per request (one per pipeline).

---

## 📝 Implementation Details

### Files Created:
1. `evaluation/accuracy_eval.py` - LLM judge + BERTScore functions
2. `scripts/run_evaluation.py` - Batch evaluation script
3. `scripts/test_accuracy.py` - Quick test script
4. `evaluation/ground_truth.json` - 15 test cases

### Files Modified:
1. `orchestration/router.py` - Wired per-query accuracy
2. `BENCHMARK.md` - Added evaluation instructions

### Dependencies Added:
- `bert-score==0.3.13` (already in requirements.txt)

---

## ✅ Verification Checklist

Before submitting:

- [ ] `python scripts/test_accuracy.py` passes
- [ ] `python scripts/run_evaluation.py --dry-run` completes
- [ ] `python scripts/run_evaluation.py` completes (full evaluation)
- [ ] `evaluation/results.json` exists with real numbers
- [ ] `BENCHMARK.md` updated with real numbers (no [TBD])
- [ ] LLM-as-a-Judge pass rate ≥90% (or documented why not)
- [ ] BERTScore F1 rescaled ≥0.55 (or documented why not)
- [ ] No "keyword match" or "fallback" in any logs

---

## 🎉 Success Criteria

**You're ready to submit when:**

✅ All tests pass  
✅ Full evaluation completes without errors  
✅ Results saved to `evaluation/results.json`  
✅ BENCHMARK.md updated with real numbers  
✅ GraphRAG shows best accuracy among all pipelines  
✅ Targets met (or close, with explanation)

---

## 📞 Need Help?

**Common Issues:**
1. Groq API key not set → Check `.env` file
2. BERTScore not installed → `pip install bert-score`
3. API not running → `python main.py` in separate terminal
4. Rate limits → Wait a few minutes, Groq resets hourly

**Debug Mode:**
```bash
# Run with verbose logging
python scripts/run_evaluation.py --dry-run 2>&1 | tee evaluation.log
```

---

**Good luck with your hackathon submission! 🚀**
