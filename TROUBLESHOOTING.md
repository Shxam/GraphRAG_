# 🔧 Troubleshooting Guide

## ❌ ERROR: Port 8000 Already in Use

**Error Message:**
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000): 
only one usage of each socket address (protocol/network address/port) is normally permitted
```

**Cause:** Another instance of the API is already running on port 8000.

---

### **SOLUTION 1: Use the Batch File (Easiest)** ✅

Double-click or run:
```bash
start_api.bat
```

This will:
1. Kill any process using port 8000
2. Start the API server

---

### **SOLUTION 2: Manual Kill (PowerShell)**

```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace XXXX with the PID from above)
taskkill /F /PID XXXX

# Start API
python main.py
```

---

### **SOLUTION 3: Use PowerShell Script**

```powershell
# Run the kill script
.\kill_port_8000.ps1

# Start API
python main.py
```

---

### **SOLUTION 4: Use Different Port**

Edit `main.py` at the bottom:
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Changed from 8000 to 8001
```

Then update evaluation script to use new port:
```bash
python scripts/run_evaluation.py --api-url http://localhost:8001
```

---

## ⚠️ WARNING: sentence-transformers not installed

**Warning Message:**
```
Warning: sentence-transformers not installed. Run: pip install sentence-transformers faiss-cpu
```

**Impact:** Basic RAG pipeline won't work (will return errors).

**Solution:**
```bash
pip install sentence-transformers faiss-cpu
```

---

## ⚠️ WARNING: redis not installed

**Warning Message:**
```
Warning: redis package not installed. Using in-memory cache.
```

**Impact:** Cache will be in-memory only (lost on restart). This is fine for evaluation.

**Solution (Optional):**
```bash
pip install redis
```

---

## ⚠️ WARNING: torchvision image extension

**Warning Message:**
```
Failed to load image Python extension: '[WinError 127] The specified procedure could not be found'
```

**Impact:** None for this project (we don't use image functionality).

**Solution:** Ignore this warning, it's harmless.

---

## ❌ ERROR: Groq client not initialized

**Error in test_accuracy.py or evaluation:**
```
✗ ERROR: Groq client not initialized
Check GROQ_API_KEY in .env file
```

**Solution:**
```bash
# Check if .env has the key
type .env | findstr GROQ_API_KEY

# If missing, add it
echo GROQ_API_KEY=your_actual_key_here >> .env
```

---

## ❌ ERROR: Connection refused

**Error in evaluation script:**
```
requests.exceptions.ConnectionError: Connection refused
```

**Cause:** API server is not running.

**Solution:**
1. Open a separate terminal
2. Run: `python main.py` or `start_api.bat`
3. Wait for: `[OK] PostMortemIQ API ready`
4. Then run evaluation in another terminal

---

## ❌ ERROR: Rate limit exceeded

**Error Message:**
```
groq.RateLimitError: Rate limit exceeded
```

**Cause:** Groq free tier limit (14,400 requests/day).

**Solution:**
1. Wait a few minutes (limits reset hourly)
2. Use `--dry-run` to test with fewer cases
3. Check remaining quota in API response

---

## ❌ ERROR: BERTScore not available

**Error in evaluation:**
```
BERTScore not available. Install with: pip install bert-score
```

**Solution:**
```bash
pip install bert-score
```

**Note:** First run downloads distilbert model (~250MB), be patient.

---

## ❌ ERROR: Ground truth not found

**Error in evaluation:**
```
FileNotFoundError: evaluation/ground_truth.json
```

**Solution:** The file should already exist. If not:
```bash
# Check if file exists
dir evaluation\ground_truth.json

# If missing, it was created in this conversation
# Check if evaluation folder exists
mkdir evaluation
```

---

## 🐌 SLOW: BERTScore taking too long

**Issue:** First BERTScore computation is slow.

**Cause:** Downloading distilbert-base-uncased model (~250MB).

**Solution:**
1. Be patient on first run (5-10 minutes)
2. Subsequent runs are fast (model cached)
3. Use `--dry-run` for quick testing

---

## 🔍 DEBUGGING: Check if API is running

```bash
# Check if port 8000 is listening
netstat -ano | findstr :8000

# Test API with curl
curl http://localhost:8000

# Or open in browser
start http://localhost:8000
```

**Expected response:**
```json
{
  "service": "PostMortemIQ",
  "version": "1.0.0",
  "description": "GraphRAG Incident Root-Cause Engine with TEE"
}
```

---

## 🔍 DEBUGGING: Check Python processes

```powershell
# List all Python processes
Get-Process python

# Kill all Python processes (CAUTION!)
Get-Process python | Stop-Process -Force
```

---

## 📊 COMMON ISSUES SUMMARY

| Issue | Quick Fix |
|-------|-----------|
| Port 8000 in use | Run `start_api.bat` |
| Groq not initialized | Check `.env` has `GROQ_API_KEY` |
| Connection refused | Start API: `python main.py` |
| BERTScore not found | `pip install bert-score` |
| sentence-transformers missing | `pip install sentence-transformers faiss-cpu` |
| Rate limit | Wait a few minutes or use `--dry-run` |

---

## ✅ VERIFICATION COMMANDS

```bash
# 1. Check dependencies
pip list | findstr "bert-score"
pip list | findstr "sentence-transformers"
pip list | findstr "groq"

# 2. Check .env
type .env

# 3. Check if API is running
curl http://localhost:8000

# 4. Check ground truth exists
dir evaluation\ground_truth.json

# 5. Test accuracy functions
python scripts/test_accuracy.py
```

---

## 🆘 STILL STUCK?

**Check these in order:**

1. ✅ Python 3.10+ installed: `python --version`
2. ✅ Dependencies installed: `pip install -r requirements.txt`
3. ✅ GROQ_API_KEY in .env: `type .env | findstr GROQ`
4. ✅ Port 8000 free: `netstat -ano | findstr :8000`
5. ✅ API starts: `python main.py`
6. ✅ Ground truth exists: `dir evaluation\ground_truth.json`
7. ✅ Test passes: `python scripts/test_accuracy.py`

If all above pass, you're ready to run evaluation! 🚀
