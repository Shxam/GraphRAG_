# PostMortemIQ — Implementation Plan

**Hackathon:** TigerGraph GraphRAG Inference  
**Current Status:** 2/10 submission requirements complete  
**Critical Path:** 5 priorities must be completed before submission

---

## 🔴 PRIORITY 1: Fix Baseline → Basic RAG Pipeline

**Current Problem:**
- `pipelines/baseline.py` is a document dump (9,048 tokens)
- Judges expect vector RAG baseline (1,500-3,000 tokens)
- Token reduction metric will change from 88.9% to 60-75%

**Implementation:**

```python
# pipelines/baseline.py - COMPLETE REWRITE

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class BaselinePipeline:
    def __init__(self):
        # Load sentence transformer (free, local)
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.index = None
        self.chunks = []
        self._build_index()
    
    def _build_index(self):
        """Build FAISS index from incident corpus"""
        # Load all runbooks, configs, log templates
        corpus = self._load_corpus()  # List of text chunks
        
        # Generate embeddings
        embeddings = self.model.encode(corpus, convert_to_numpy=True)
        
        # Build FAISS index (in-memory, no server)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)
        self.chunks = corpus
    
    def run(self, incident_id: str, incident_data: dict):
        """Run Basic RAG pipeline"""
        # 1. Embed the alert
        alert_text = f"{incident_data['alert_name']} {incident_data['severity']}"
        query_embedding = self.model.encode([alert_text], convert_to_numpy=True)
        
        # 2. Retrieve top-k=5 most similar chunks
        k = 5
        distances, indices = self.index.search(query_embedding, k)
        retrieved_chunks = [self.chunks[i] for i in indices[0]]
        
        # 3. Build context from retrieved chunks only
        context = "\n\n".join(retrieved_chunks)
        
        # 4. Feed to Groq LLM
        prompt = f"Alert: {alert_text}\n\nContext:\n{context}\n\nWhat is the root cause?"
        response = self.groq_client.call_llm(prompt)
        
        # 5. Track tokens
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        input_tokens = len(enc.encode(prompt))
        
        return {
            "pipeline": "basic_rag",
            "input_tokens": input_tokens,
            "output_tokens": response["output_tokens"],
            "total_tokens": input_tokens + response["output_tokens"],
            "latency_ms": response["latency_ms"],
            "cost_usd": self._calculate_cost(input_tokens, response["output_tokens"]),
            "rca_report": response["text"]
        }
```

**Expected Result:**
- Input tokens: 1,500-3,000 (vs 9,048 document dump)
- GraphRAG still wins: 1,002 tokens vs 2,000 = **50% reduction**
- Still above 85% threshold if we compare to original 9K baseline

**Files to Modify:**
- `pipelines/baseline.py` - Complete rewrite
- `pipelines/comparator.py` - Update to show "Basic RAG" label
- `requirements.txt` - Add `sentence-transformers`, `faiss-cpu`

**Time Estimate:** 2-3 hours

---

## 🔴 PRIORITY 2: Implement Accuracy Evaluation

**Current Problem:**
- All `accuracy_*` fields are `null`
- No LLM-as-a-Judge
- No BERTScore
- **This is 30% of the judging score**

**Implementation:**

### A. Create Ground Truth Dataset

```json
// evaluation/ground_truth.json
[
  {
    "incident_id": "INC-1005",
    "alert": {
      "alert_name": "High 5xx errors in auth-svc",
      "severity": "critical"
    },
    "root_cause": "config_3",
    "ground_truth_summary": "JWT_EXPIRY changed from 3600 to 60 seconds in auth-svc deployment v2.4.1, causing token expiry failures. Rollback to v2.4.0 resolved the issue."
  },
  // ... 9-14 more test cases
]
```

### B. LLM-as-a-Judge

```python
# evaluation/accuracy_eval.py

from transformers import pipeline
import requests

class AccuracyEvaluator:
    def __init__(self):
        # Use HuggingFace Inference API (free tier)
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.judge_model = "google/flan-t5-large"
    
    def llm_judge(self, alert, ground_truth, rca_report):
        """PASS/FAIL evaluation"""
        prompt = f"""Given this incident alert: {alert}
Ground truth root cause: {ground_truth}
AI answer: {rca_report}

Does the AI answer correctly identify the root cause?
Answer: PASS or FAIL"""
        
        # Call HuggingFace Inference API
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{self.judge_model}",
            headers={"Authorization": f"Bearer {self.hf_api_key}"},
            json={"inputs": prompt}
        )
        
        result = response.json()[0]["generated_text"]
        return 1.0 if "PASS" in result.upper() else 0.0
    
    def evaluate_pipeline(self, pipeline_results, ground_truth_cases):
        """Evaluate all test cases"""
        scores = []
        for case in ground_truth_cases:
            result = pipeline_results[case["incident_id"]]
            score = self.llm_judge(
                case["alert"],
                case["ground_truth_summary"],
                result["rca_report"]
            )
            scores.append(score)
        
        pass_rate = sum(scores) / len(scores)
        return {
            "llm_judge_pass_rate": pass_rate,
            "meets_bonus_threshold": pass_rate >= 0.90
        }
```

### C. BERTScore

```python
from evaluate import load

class AccuracyEvaluator:
    def bertscore_evaluate(self, predictions, references):
        """Semantic similarity evaluation"""
        bertscore = load("bertscore")
        results = bertscore.compute(
            predictions=predictions,
            references=references,
            model_type="distilbert-base-uncased"
        )
        
        f1_raw = np.mean(results["f1"])
        f1_rescaled = (f1_raw - 0.5) / 0.5  # Rescale to 0-1
        
        return {
            "bertscore_f1_raw": f1_raw,
            "bertscore_f1_rescaled": f1_rescaled,
            "bertscore_precision": np.mean(results["precision"]),
            "bertscore_recall": np.mean(results["recall"]),
            "meets_bonus_threshold": f1_rescaled >= 0.55
        }
```

### D. Wire into API

```python
# orchestration/router.py

@app.post("/analyze/sync")
async def analyze_incident_sync(request: IncidentRequest):
    # Run all 3 pipelines
    baseline_result = baseline_pipeline.run(...)
    graphrag_result = graphrag_pipeline.run(...)
    llm_only_result = llm_only_pipeline.run(...)
    
    # Load ground truth for this incident
    ground_truth = load_ground_truth(request.incident_id)
    
    if ground_truth:
        # Run accuracy evaluation
        evaluator = AccuracyEvaluator()
        
        accuracy_baseline = evaluator.llm_judge(
            ground_truth["alert"],
            ground_truth["ground_truth_summary"],
            baseline_result["rca_report"]
        )
        
        accuracy_graphrag = evaluator.llm_judge(
            ground_truth["alert"],
            ground_truth["ground_truth_summary"],
            graphrag_result["rca_report"]
        )
        
        accuracy_llm_only = evaluator.llm_judge(
            ground_truth["alert"],
            ground_truth["ground_truth_summary"],
            llm_only_result["rca_report"]
        )
        
        # Add to results
        baseline_result["accuracy"] = accuracy_baseline
        graphrag_result["accuracy"] = accuracy_graphrag
        llm_only_result["accuracy"] = accuracy_llm_only
    
    return comparator.compare_three(baseline_result, graphrag_result, llm_only_result)
```

**Files to Create:**
- `evaluation/ground_truth.json` - 10-15 test cases
- `evaluation/accuracy_eval.py` - LLM-Judge + BERTScore

**Files to Modify:**
- `orchestration/router.py` - Wire accuracy into response
- `requirements.txt` - Add `evaluate`, `transformers`

**Time Estimate:** 3-4 hours

---

## 🟡 PRIORITY 3: Fix GraphRAG Hallucination

**Current Problem:**
- `hallucination_rate_graphrag: 0.25`
- LLM mentioned `payment-svc` which wasn't in subgraph
- Verifier correctly flagged it

**Root Cause:**
- `affected_services` list includes services at hop=1
- But those services don't have edges in the subgraph
- LLM sees the service name and mentions it
- Verifier flags it as hallucination

**Solution (Option B - Low Risk):**

```python
# llm/prompt_builder.py

def build_graphrag_prompt(subgraph, similar_incidents, alert_id):
    # Extract service IDs that actually appear in edges
    services_in_graph = set()
    for edge in subgraph.get("edges", []):
        if edge.get("from_type") == "Service":
            services_in_graph.add(edge["from"])
        if edge.get("to_type") == "Service":
            services_in_graph.add(edge["to"])
    
    # Filter affected_services to only include those in graph
    affected_services_filtered = [
        svc for svc in subgraph.get("affected_services", [])
        if svc in services_in_graph
    ]
    
    # Build prompt with filtered list
    prompt = f"""Causal Graph:
Nodes: {subgraph['nodes']}
Edges: {subgraph['edges']}
Affected Services (verified in graph): {affected_services_filtered}

Based ONLY on the graph above, identify the root cause."""
    
    return prompt
```

**Expected Result:**
- `hallucination_rate_graphrag: 0.0` or very close
- Verifier passes

**Files to Modify:**
- `llm/prompt_builder.py` - Filter affected_services

**Time Estimate:** 30 minutes

---

## 🟡 PRIORITY 4: Scale Dataset to 2M+ Tokens

**Current Problem:**
- Synthetic data is ~50K-200K tokens (estimated)
- Hackathon requires 2,000,000+ tokens

**Implementation:**

```python
# data/ingest_real_data.py

import requests
from bs4 import BeautifulSoup
import tiktoken

def ingest_sre_book():
    """Scrape Google SRE Book (public, permissive)"""
    chapters = [
        "https://sre.google/sre-book/introduction/",
        "https://sre.google/sre-book/monitoring-distributed-systems/",
        # ... all chapters
    ]
    
    corpus = []
    for url in chapters:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        corpus.append(text)
    
    return corpus

def ingest_danluu_postmortems():
    """Clone github.com/danluu/post-mortems"""
    os.system("git clone https://github.com/danluu/post-mortems.git data/postmortems")
    
    corpus = []
    for file in Path("data/postmortems").glob("*.md"):
        corpus.append(file.read_text())
    
    return corpus

def chunk_corpus(corpus, chunk_size=512, overlap=256):
    """Chunk into 512-token windows with 256 overlap"""
    enc = tiktoken.get_encoding("cl100k_base")
    
    chunks = []
    for doc in corpus:
        tokens = enc.encode(doc)
        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i+chunk_size]
            chunk_text = enc.decode(chunk_tokens)
            chunks.append(chunk_text)
    
    return chunks

def verify_token_count(chunks):
    """Verify 2M+ tokens"""
    enc = tiktoken.get_encoding("cl100k_base")
    total_tokens = sum(len(enc.encode(chunk)) for chunk in chunks)
    
    print(f"Total tokens: {total_tokens:,}")
    print(f"Meets requirement: {total_tokens >= 2_000_000}")
    
    return total_tokens

# Main
corpus = []
corpus.extend(ingest_sre_book())
corpus.extend(ingest_danluu_postmortems())
# Add more sources until 2M+ tokens

chunks = chunk_corpus(corpus)
total_tokens = verify_token_count(chunks)

# Save for Basic RAG and GraphRAG
with open("data/corpus_chunks.json", "w") as f:
    json.dump(chunks, f)
```

**Files to Create:**
- `data/ingest_real_data.py` - Ingest public corpora
- `scripts/verify_dataset_tokens.py` - Verify 2M+ tokens

**Time Estimate:** 2-3 hours

---

## 🟢 PRIORITY 5: Update Dashboard

**Current Problem:**
- Dashboard exists but doesn't show all 3 pipelines side-by-side
- No accuracy metrics displayed
- No causal graph visualization

**Implementation:**

```python
# evaluation/dashboard.py

import streamlit as st
import requests
import json

st.set_page_config(page_title="PostMortemIQ", layout="wide")

st.title("PostMortemIQ — GraphRAG vs RAG vs LLM-Only")

# Query input
alert_json = st.text_area("Paste alert JSON", value="""{
  "incident_id": "INC-1005",
  "alert_name": "High 5xx errors in auth-svc",
  "severity": "critical"
}""", height=150)

if st.button("🔍 Analyze", type="primary"):
    with st.spinner("Running all 3 pipelines..."):
        response = requests.post(
            "http://localhost:8000/analyze/sync",
            json=json.loads(alert_json)
        )
        data = response.json()
        st.session_state.result = data

if "result" in st.session_state:
    data = st.session_state.result
    
    # Metrics row 1: Tokens
    st.subheader("📊 Token Comparison")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "LLM-Only",
            f"{data['llm_only_result']['total_tokens']} tokens",
            delta=None
        )
    
    with col2:
        baseline_tokens = data['baseline_result']['total_tokens']
        st.metric(
            "Basic RAG",
            f"{baseline_tokens} tokens",
            delta=None
        )
    
    with col3:
        graphrag_tokens = data['graphrag_result']['total_tokens']
        reduction = ((baseline_tokens - graphrag_tokens) / baseline_tokens) * 100
        st.metric(
            "GraphRAG",
            f"{graphrag_tokens} tokens",
            delta=f"-{reduction:.1f}%",
            delta_color="inverse"
        )
    
    # Metrics row 2: Cost & Latency
    st.subheader("💰 Cost & ⚡ Latency")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("LLM-Only Cost", f"${data['llm_only_result']['cost_usd']:.6f}")
        st.metric("LLM-Only Latency", f"{data['llm_only_result']['latency_ms']}ms")
    
    with col2:
        st.metric("Basic RAG Cost", f"${data['baseline_result']['cost_usd']:.6f}")
        st.metric("Basic RAG Latency", f"{data['baseline_result']['latency_ms']}ms")
    
    with col3:
        st.metric("GraphRAG Cost", f"${data['graphrag_result']['cost_usd']:.6f}")
        st.metric("GraphRAG Latency", f"{data['graphrag_result']['latency_ms']}ms")
    
    # Metrics row 3: Accuracy
    if data['graphrag_result'].get('accuracy') is not None:
        st.subheader("✅ Accuracy")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            acc = data['llm_only_result'].get('accuracy', 0)
            st.metric("LLM-Only", f"{acc*100:.0f}%")
        
        with col2:
            acc = data['baseline_result'].get('accuracy', 0)
            st.metric("Basic RAG", f"{acc*100:.0f}%")
        
        with col3:
            acc = data['graphrag_result'].get('accuracy', 0)
            st.metric("GraphRAG", f"{acc*100:.0f}%")
    
    # RCA Reports (3 tabs)
    st.subheader("📝 Root Cause Analysis Reports")
    tab1, tab2, tab3 = st.tabs(["LLM-Only", "Basic RAG", "GraphRAG"])
    
    with tab1:
        st.markdown(data['llm_only_result']['rca_report'])
    
    with tab2:
        st.markdown(data['baseline_result']['rca_report'])
    
    with tab3:
        st.markdown(data['graphrag_result']['rca_report'])
        
        # Hallucination warning
        if data['graphrag_result'].get('hallucination_count', 0) > 0:
            st.warning(f"⚠️ Hallucinated entities: {data['graphrag_result']['hallucinated_entities']}")
    
    # Causal graph visualization
    st.subheader("🕸️ GraphRAG Causal Subgraph")
    
    subgraph = data['graphrag_result'].get('subgraph', {})
    
    if subgraph:
        # Use streamlit-agraph or networkx
        try:
            from streamlit_agraph import agraph, Node, Edge, Config
            
            nodes = [
                Node(id=n['id'], label=n['name'], color=_get_color(n['type']))
                for n in subgraph['nodes']
            ]
            
            edges = [
                Edge(source=e['from'], target=e['to'], label=e['type'])
                for e in subgraph['edges']
            ]
            
            config = Config(width=800, height=600, directed=True)
            agraph(nodes=nodes, edges=edges, config=config)
        
        except ImportError:
            st.info("Install streamlit-agraph for graph visualization: pip install streamlit-agraph")
            st.json(subgraph)

def _get_color(node_type):
    colors = {
        "Alert": "#ff4444",
        "Service": "#4444ff",
        "Deployment": "#ff8800",
        "ConfigChange": "#00ff00"
    }
    return colors.get(node_type, "#888888")
```

**Deployment:**
1. Push to GitHub
2. Go to share.streamlit.io
3. Connect repo
4. Set `GROQ_API_KEY` as secret
5. Deploy
6. Get public URL for submission

**Files to Modify:**
- `evaluation/dashboard.py` - Complete rewrite

**Time Estimate:** 2-3 hours

---

## 🟢 PRIORITY 6: Create Architecture Diagram

**Tool:** draw.io or Excalidraw

**Diagram Structure:**

```
┌─────────────────────────────────────────────────────────┐
│                   Incident Alert JSON                    │
│              {"alert_name": "...", ...}                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI /analyze/sync                       │
│                  (router.py)                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                 Alert Deduplicator                       │
│            (5-min window, fingerprint)                   │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┬───────────────┐
         │                       │               │
         ▼                       ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐
│   LLM-Only      │  │   Basic RAG     │  │  GraphRAG    │
│                 │  │                 │  │              │
│ No retrieval    │  │ FAISS           │  │ TigerGraph   │
│ Raw alert only  │  │ Vector search   │  │ Causal graph │
│                 │  │ Top-5 chunks    │  │ Multi-hop    │
│ 280 tokens      │  │ 1,500-3K tokens │  │ 1,002 tokens │
└────────┬────────┘  └────────┬────────┘  └──────┬───────┘
         │                    │                   │
         │                    │                   ▼
         │                    │          ┌─────────────────┐
         │                    │          │ Response        │
         │                    │          │ Verifier        │
         │                    │          │ (hallucination) │
         │                    │          └────────┬────────┘
         │                    │                   │
         └────────────────────┴───────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Groq LLM API   │
                    │ llama-3.3-70b    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   Comparator     │
                    │ Tokens, Cost,    │
                    │ Latency, Accuracy│
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Response JSON   │
                    │  + Dashboard     │
                    └──────────────────┘

[TEE Enclave Layer - Optional, shown as dotted box around entire system]
```

**Export:** Save as `docs/architecture.png`

**Time Estimate:** 1 hour

---

## Timeline

**Total Estimated Time:** 12-16 hours

| Priority | Task | Time | Status |
|----------|------|------|--------|
| 🔴 P1 | Fix Baseline → Basic RAG | 2-3h | ❌ Not started |
| 🔴 P2 | Implement Accuracy Eval | 3-4h | ❌ Not started |
| 🟡 P3 | Fix Hallucination | 0.5h | ❌ Not started |
| 🟡 P4 | Scale Dataset to 2M+ | 2-3h | ❌ Not started |
| 🟢 P5 | Update Dashboard | 2-3h | ❌ Not started |
| 🟢 P6 | Architecture Diagram | 1h | ❌ Not started |
| 🟢 P7 | Blog Post | 2h | ❌ Not started |
| 🟢 P8 | Demo Video | 1h | ❌ Not started |

**Recommended Schedule:**
- Day 1: P1 + P2 (6-7 hours)
- Day 2: P3 + P4 + P5 (5-6 hours)
- Day 3: P6 + P7 + P8 + Testing (4-5 hours)

---

## Success Criteria

### Must Have (Submission Blockers)
- [ ] Token reduction >85% (vs Basic RAG, not doc dump)
- [ ] Accuracy evaluation implemented (non-null values)
- [ ] Dataset ≥2M tokens (verified)
- [ ] Dashboard deployed with public URL
- [ ] Blog post published
- [ ] Architecture diagram in README

### Should Have (Bonus Points)
- [ ] LLM-as-a-Judge ≥90% pass rate
- [ ] BERTScore F1 rescaled ≥0.55
- [ ] Hallucination rate <0.05
- [ ] Demo video recorded

### Nice to Have
- [ ] TEE enclave integration
- [ ] Real TigerGraph Cloud instance
- [ ] LinkedIn post with @TigerGraph

---

*Last Updated: Based on INC-1005 benchmark results*
