# 🚀 Quick Deploy to Streamlit Cloud

## Fastest Path (Recommended)

### Step 1: Prepare
```powershell
.\prepare_streamlit_deploy.ps1
```

### Step 2: Commit & Push
```bash
git add .
git commit -m "Deploy to Streamlit Cloud"
git push
```

### Step 3: Deploy
1. Go to **https://share.streamlit.io**
2. Click **"New app"**
3. Select your repository: `graphrag_` (or your repo name)
4. Set **Main file path**: `evaluation/dashboard.py`
5. Set **Python version**: `3.11`
6. Click **"Deploy!"**

### Step 4: Restore (After Deployment)
```powershell
.\restore_requirements.ps1
```

---

## Alternative: Manual Deploy

If scripts don't work, manually:

1. **Backup requirements:**
   ```bash
   cp requirements.txt requirements-full.txt
   cp requirements-streamlit.txt requirements.txt
   ```

2. **Commit and push**

3. **Deploy on Streamlit Cloud** (same as above)

4. **Restore requirements:**
   ```bash
   cp requirements-full.txt requirements.txt
   ```

---

## Deployment Settings

| Setting | Value |
|---------|-------|
| Main file | `evaluation/dashboard.py` |
| Python version | `3.11` |
| Branch | `main` |

---

## What Was Fixed?

✅ `tiktoken` - Updated to version with prebuilt wheels  
✅ `faiss-cpu` - Using compatible version (1.12.0+)  
✅ `grpcio` - Allowing prebuilt wheels  
✅ `numpy` - Pinned to avoid v2.0 issues  
✅ Python version - Locked to 3.11.0  

---

## Need Help?

See `STREAMLIT_DEPLOYMENT.md` for detailed guide  
See `DEPLOYMENT_FIX_SUMMARY.md` for technical details
