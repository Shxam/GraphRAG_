# ✅ Streamlit Cloud Deployment Checklist

## Pre-Deployment

- [ ] All changes committed to Git
- [ ] Repository pushed to GitHub
- [ ] `.python-version` file contains `3.11.0`
- [ ] `requirements.txt` or `requirements-streamlit.txt` is ready

## Deployment Preparation

### Option A: Minimal Requirements (Fastest)
- [ ] Run `.\prepare_streamlit_deploy.ps1`
- [ ] Verify `requirements.txt` now has minimal dependencies
- [ ] Commit and push changes

### Option B: Full Requirements
- [ ] Verify `requirements.txt` has updated package versions:
  - [ ] `tiktoken>=0.8.0`
  - [ ] `faiss-cpu>=1.12.0`
  - [ ] `numpy>=1.26.4,<2.0.0`
  - [ ] `grpcio>=1.64.1`
- [ ] Commit and push changes

## Streamlit Cloud Setup

- [ ] Go to https://share.streamlit.io
- [ ] Sign in with GitHub
- [ ] Click "New app"
- [ ] Select repository: `graphrag_` (or your repo name)
- [ ] Select branch: `main`
- [ ] Set main file path: `evaluation/dashboard.py`
- [ ] Click "Advanced settings"
- [ ] Set Python version: `3.11`
- [ ] Click "Deploy!"

## Post-Deployment

- [ ] Wait for deployment to complete (5-10 minutes)
- [ ] Check deployment logs for errors
- [ ] Test dashboard functionality:
  - [ ] Dashboard loads without errors
  - [ ] Single Query tab works
  - [ ] Benchmark Dashboard tab displays
  - [ ] Graph Visualization tab loads
  - [ ] TEE Attestation tab shows data
- [ ] If using Option A, run `.\restore_requirements.ps1` locally

## Troubleshooting

If deployment fails:

- [ ] Check deployment logs in Streamlit Cloud
- [ ] Verify Python version is set to `3.11`
- [ ] Try "Reboot app" in Streamlit Cloud
- [ ] Try "Clear cache" in Streamlit Cloud settings
- [ ] Switch to minimal requirements if full requirements fail
- [ ] Check `.python-version` file
- [ ] Verify all files are committed and pushed

## Environment Variables (Optional)

If connecting to live API:

- [ ] Go to Streamlit Cloud app settings
- [ ] Click "Secrets"
- [ ] Add required secrets:
  ```toml
  API_URL = "your-api-url"
  GROQ_API_KEY = "your-key"
  TG_HOST = "your-tigergraph-host"
  TG_USERNAME = "your-username"
  TG_PASSWORD = "your-password"
  ```
- [ ] Save secrets
- [ ] Reboot app

## Success Criteria

✅ Dashboard is accessible at your Streamlit Cloud URL  
✅ No errors in deployment logs  
✅ All tabs load correctly  
✅ Demo data displays properly  
✅ UI is responsive and functional  

## Resources

- 📖 [QUICK_DEPLOY.md](QUICK_DEPLOY.md) - Quick deployment guide
- 📖 [STREAMLIT_DEPLOYMENT.md](STREAMLIT_DEPLOYMENT.md) - Detailed deployment guide
- 📖 [DEPLOYMENT_FIX_SUMMARY.md](DEPLOYMENT_FIX_SUMMARY.md) - Technical details
- 🔗 [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- 🔗 [Streamlit Forum](https://discuss.streamlit.io/)

## Notes

Date: _________________  
Deployed by: _________________  
Deployment URL: _________________  
Status: ⬜ Success ⬜ Failed ⬜ In Progress  
Issues encountered: _________________
