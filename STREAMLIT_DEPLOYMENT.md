# Streamlit Cloud Deployment Guide

## Quick Deploy to Streamlit Cloud

### Option 1: Use Minimal Requirements (Recommended)

1. **Rename requirements file temporarily:**
   ```bash
   mv requirements.txt requirements-full.txt
   mv requirements-streamlit.txt requirements.txt
   ```

2. **Deploy to Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Set main file path: `evaluation/dashboard.py`
   - Python version: `3.11`
   - Deploy!

3. **After deployment, restore original requirements:**
   ```bash
   mv requirements.txt requirements-streamlit.txt
   mv requirements-full.txt requirements.txt
   ```

### Option 2: Use Full Requirements (May have build issues)

If you need the full requirements.txt for local development:

1. **Ensure Python version is set correctly:**
   - Check `.python-version` file contains: `3.11.0`

2. **Deploy with these settings:**
   - Main file: `evaluation/dashboard.py`
   - Python version: `3.11`
   - Advanced settings → Secrets: Add your API keys if needed

### Troubleshooting

#### Issue: `faiss-cpu` version not found
**Solution:** The requirements.txt now uses `faiss-cpu>=1.12.0` which is compatible with Python 3.10+

#### Issue: `tiktoken` requires Rust compiler
**Solution:** Updated to `tiktoken>=0.8.0` which has prebuilt wheels

#### Issue: `grpcio` build fails
**Solution:** Changed to `grpcio>=1.64.1` to allow prebuilt wheels

#### Issue: Python 3.14 is being used
**Solution:** 
- Ensure `.python-version` contains `3.11.0`
- In Streamlit Cloud settings, explicitly set Python version to `3.11`

### Environment Variables

If your dashboard needs to connect to a live API, add these secrets in Streamlit Cloud:

```toml
# .streamlit/secrets.toml (for Streamlit Cloud)
API_URL = "https://your-api-endpoint.com"
GROQ_API_KEY = "your-groq-api-key"
TG_HOST = "your-tigergraph-host"
TG_USERNAME = "your-username"
TG_PASSWORD = "your-password"
```

### Local Testing

Test the dashboard locally before deploying:

```bash
# Install minimal requirements
pip install -r requirements-streamlit.txt

# Run dashboard
streamlit run evaluation/dashboard.py
```

### Dashboard Features

The dashboard works in two modes:

1. **Standalone Mode** (default): Shows demo data and UI without backend API
2. **Connected Mode**: Connects to your FastAPI backend for live data

The dashboard will gracefully handle API unavailability and show demo data.

### Files for Deployment

- `requirements-streamlit.txt` - Minimal dependencies for dashboard only
- `requirements.txt` - Full dependencies for complete application
- `.python-version` - Python version specification (3.11.0)
- `.streamlit/config.toml` - Streamlit configuration
- `packages.txt` - System-level dependencies (if needed)

### Support

For issues with Streamlit Cloud deployment:
- Check [Streamlit Community Forum](https://discuss.streamlit.io/)
- Review [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
