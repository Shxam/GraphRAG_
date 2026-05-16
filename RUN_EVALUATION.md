# 🚀 Run Evaluation - Step by Step

## ✅ Prerequisites Complete
- [x] BERTScore installed
- [x] Ground truth dataset created (15 test cases)
- [x] Evaluation scripts created
- [x] Router.py updated with accuracy wiring

---

## 📋 EXECUTION STEPS

### **Step 1: Test Accuracy Functions** (2 minutes)

Open a terminal and run:

```bash
cd C:\Users\SHAM\OneDrive\Desktop\graphRAG
python scripts/test_accuracy.py
```

**Expected Output:**
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

**If you see errors:**
- "Groq client not initialized" → Check GROQ_API_KEY in .env
- "BERTScore not available" → Run `pip install bert-score` again

---

### **Step 2: Generate Synthetic Incidents** (1 minute)

The pipelines need incident data to retrieve from. Generate it:

```bash
python data/generate_incidents.py
```

**This creates:** `data/synthetic_incidents.json`

**If this fails:** The evaluation can still run, but pipelines may return empty results.

---

### **Step 3: Start the API Server** (Keep running)

Open a **NEW terminal** and run:

```bash
cd C:\Users\SHAM\OneDrive\Desktop\graphRAG
python main.py
```

**Expected Output:**
```
[OK] PostMortemIQ API ready
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal open!** The API must be running for evaluation.

---

### **Step 4: Run Dry Run Evaluation** (2-3 minutes)

Open a **THIRD terminal** and run:

```bash
cd C:\Users\SHAM\OneDrive\Desktop\graphRAG
python scripts/run_evaluation.py --dry-run
```

**What this does:**
- Tests with first 3 incidents only
- Calls API for each incident
- Runs LLM-as-a-Judge (3 cases × 4 pipelines = 12 judge calls)
- Computes BERTScore
- Saves results to `evaluation/results.json`

**Expected Output:**
```
PostMortemIQ Batch Evaluation
================================================================================

Loading ground truth test cases...
DRY RUN MODE: Testing with first 3 cases only
Loaded 3 test cases

Initializing Groq client for LLM-as-a-Judge...
✓ Groq client ready

Running evaluation on test cases...
--------------------------------------------------------------------------------
[1/3] INC-1005: High 5xx errors in auth-svc
  ✓ graphrag: PASS
  ✓ basic_rag: PASS
  ✗ llm_only: FAIL
  ✓ baseline: PASS

[2/3] incident_1: High error rate in auth-svc
  ✓ graphrag: PASS
  ✓ basic_rag: PASS
  ✗ llm_only: FAIL
  ✓ baseline: PASS

[3/3] incident_2: Database connection pool exhaustion
  ✓ graphrag: PASS
  ✓ basic_rag: PASS
  ✗ llm_only: FAIL
  ✓ baseline: PASS

--------------------------------------------------------------------------------

Computing aggregate metrics...

graphrag:
  LLM-Judge Pass Rate: 100.0%
  BERTScore F1 (raw): 0.9123
  BERTScore F1 (rescaled): 0.4519
  Cases evaluated: 3

✓ Results saved to evaluation/results.json

================================================================================
SUMMARY TABLE
================================================================================

Pipeline         Pass Rate    F1 Raw     F1 Rescaled  Cases   
--------------------------------------------------------------------------------
llm_only         0.0%         0.8456     0.0350       3       
basic_rag        100.0%       0.8987     0.3669       3       
graphrag         100.0%       0.9123     0.4519       3       
baseline         100.0%       0.9045     0.4031       3       

TARGET ACHIEVEMENT:
  LLM-Judge ≥90%: ✓ PASS (100.0%)
  BERTScore F1 ≥0.55: ✗ FAIL (0.4519)
```

**If dry run succeeds, proceed to full evaluation!**

---

### **Step 5: Run Full Evaluation** (10-15 minutes)

```bash
python scripts/run_evaluation.py
```

**What this does:**
- Evaluates all 15 test cases
- 15 cases × 4 pipelines = 60 API calls
- 60 LLM-as-a-Judge calls
- Computes aggregate BERTScore
- Saves final results

**Expected Output:**
```
PostMortemIQ Batch Evaluation
================================================================================

Loading ground truth test cases...
Loaded 15 test cases

Running evaluation on test cases...
[1/15] INC-1005: High 5xx errors in auth-svc
  ✓ graphrag: PASS
  ✓ basic_rag: PASS
  ✗ llm_only: FAIL
  ✓ baseline: PASS

[2/15] incident_1: High error rate in auth-svc
  ✓ graphrag: PASS
  ...

[15/15] incident_15: Elasticsearch cluster red status
  ✓ graphrag: PASS
  ✓ basic_rag: PASS
  ✗ llm_only: FAIL
  ✓ baseline: PASS

================================================================================
SUMMARY TABLE
================================================================================

Pipeline         Pass Rate    F1 Raw     F1 Rescaled  Cases   
--------------------------------------------------------------------------------
llm_only         60.0%        0.8654     0.1588       15      
basic_rag        86.7%        0.9123     0.4519       15      
graphrag         93.3%        0.9287     0.5544       15      
baseline         80.0%        0.8891     0.3069       15      

TARGET ACHIEVEMENT:
  LLM-Judge ≥90%: ✓ PASS (93.3%)
  BERTScore F1 ≥0.55: ✓ PASS (0.5544)

✓ Evaluation complete!
```

---

### **Step 6: Check Results**

```bash
# View results file
type evaluation\results.json

# Or open in editor
code evaluation\results.json
```

**Results format:**
```json
{
  "run_timestamp": "2026-05-16T...",
  "total_cases": 15,
  "graphrag": {
    "llm_judge_pass_rate": 0.9333,
    "bertscore_f1_raw": 0.9287,
    "bertscore_f1_rescaled": 0.5544,
    "total_evaluated": 15
  },
  "basic_rag": {...},
  "llm_only": {...},
  "baseline": {...}
}
```

---

### **Step 7: Update BENCHMARK.md**

Open `BENCHMARK.md` and replace [TBD] values with real numbers from `evaluation/results.json`:

**Example:**
```markdown
| **LLM-as-a-Judge pass rate** | **60.0%** | **86.7%** | **93.3%** ✅ | **80.0%** |
| **BERTScore F1 (rescaled)** | **0.16** | **0.45** | **0.55** ✅ | **0.31** |
```

---

## 🔧 TROUBLESHOOTING

### Error: "Groq client not initialized"
```bash
# Check .env file
type .env | findstr GROQ_API_KEY

# If missing, add it
echo GROQ_API_KEY=your_key_here >> .env
```

### Error: "Connection refused" or "API timeout"
- Make sure API is running: `python main.py` in separate terminal
- Check API is accessible: Open http://localhost:8000 in browser

### Error: "Rate limit exceeded"
- Groq free tier: 14,400 requests/day
- Wait a few minutes and retry
- Or use `--dry-run` to test with fewer cases

### Low Pass Rate (<90%)
- Check if pipelines are returning good RCA reports
- Verify ground truth summaries are accurate
- Try tuning prompts in `llm/prompt_builder.py`

### BERTScore taking too long
- First run downloads distilbert model (~250MB)
- Subsequent runs are faster (model cached)
- Use `--dry-run` for quick testing

---

## 📊 WHAT TO EXPECT

### Timing:
- **Test accuracy:** 30 seconds
- **Dry run (3 cases):** 2-3 minutes
- **Full evaluation (15 cases):** 10-15 minutes

### Groq API Calls:
- **Dry run:** 3 cases × 4 pipelines × 2 (pipeline + judge) = 24 calls
- **Full evaluation:** 15 cases × 4 pipelines × 2 = 120 calls
- **Well within free tier:** 14,400 requests/day

### Results:
- **Pass rates:** GraphRAG should be highest (90%+)
- **BERTScore:** GraphRAG should be highest (0.55+)
- **Token reduction:** GraphRAG vs Basic RAG (~50-60%)

---

## ✅ SUCCESS CHECKLIST

After running full evaluation:

- [ ] `evaluation/results.json` exists
- [ ] GraphRAG pass rate ≥90%
- [ ] GraphRAG BERTScore F1 ≥0.55
- [ ] All 4 pipelines evaluated (15 cases each)
- [ ] No errors in console output
- [ ] BENCHMARK.md updated with real numbers

---

## 🎉 YOU'RE DONE!

Once evaluation completes successfully:

1. ✅ Real accuracy metrics obtained
2. ✅ LLM-as-a-Judge working
3. ✅ BERTScore computed
4. ✅ Results saved to JSON
5. ✅ Ready for hackathon submission!

---

## 📞 QUICK COMMANDS REFERENCE

```bash
# Test accuracy functions
python scripts/test_accuracy.py

# Generate synthetic data
python data/generate_incidents.py

# Start API (keep running)
python main.py

# Dry run (3 cases)
python scripts/run_evaluation.py --dry-run

# Full evaluation (15 cases)
python scripts/run_evaluation.py

# View results
type evaluation\results.json
```

---

**Good luck! 🚀**
