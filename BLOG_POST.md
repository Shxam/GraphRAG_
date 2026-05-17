# How I Built a Resilient GraphRAG Engine for Instant Root-Cause Analysis (And Proved Graphs Beat Tokens)

**TL;DR:** PostMortemIQ is a GraphRAG-powered incident RCA system built for the TigerGraph Hackathon. It outperforms standard RAG by traversing topological dependencies instead of noisy vector similarity. The result? A **78.9% token reduction**, **83.3% lower cost**, **72.2% faster latency**, and a robust **0.625 BERTScore F1**. Plus, it features a 4-provider resilient LLM fallback chain to completely eliminate rate limits. 

---

## The Problem: On-Call Engineers Are Flying Blind

When a production incident fires at 2 AM, an on-call Site Reliability Engineer (SRE) has seconds to answer three questions:
1. What broke?
2. Why did it break?
3. What do I do?

Traditional tools force engineers to manually correlate data across noisy logs, sprawling dashboards, deployment histories, and configuration changes. This "swivel-chair investigation" often takes **30–60 minutes**. Every minute of downtime costs real money.

LLMs can theoretically help analyze this data—but they have a critical flaw. They require enormous amounts of context to piece together the timeline of what went wrong, and **context is expensive**.

A typical brute-force LLM analysis requires dumping all available data:
- Alert details → 500 tokens
- Service logs → 3,000 tokens  
- Deployment history → 2,000 tokens
- Config changes → 1,500 tokens
- Related past incidents → 2,000 tokens

**Total: ~9,000 tokens per query.** At enterprise scale across thousands of microservices, that token consumption becomes financially unsustainable.

---

## The Solution: GraphRAG + TigerGraph

Instead of dumping a massive mountain of unstructured logs into the LLM, **PostMortemIQ** uses TigerGraph's multi-hop graph traversal to surgically extract exactly the right context. It finds the *causal chain* that perfectly explains the incident.

```
Alert: "High 5xx errors in auth-svc"
    ↓ TigerGraph GSQL Traversal
ConfigChange: JWT_EXPIRY changed 3600→60
    ↓ directly_affects
Service: auth-svc
    ↓ calls
Service: api-gateway
```

By mapping the system topology, this causal subgraph condenses the necessary context down to just **~380 tokens**. It completely eliminates the noise and provides the LLM with the exact causal relationships it needs to diagnose the issue.

---

## Architecture: A Multi-Provider Resilient System

![PostMortemIQ Architecture](architecture.png)

```
Alert JSON (PagerDuty/Datadog)
        ↓
FastAPI Server :8000
  └── Deduplicator (SHA-256 fingerprint)
        ↓
┌─────────────────────────────────────────┐
│  GraphRAG  │  BasicRAG  │  LLM-Only    │
│ TigerGraph │   FAISS    │   Direct     │
│  380 tok   │  1,800 tok │   294 tok    │
└─────────────────────────────────────────┘
        ↓
   Multi-Provider Resilient LLM Chain
   Groq → Ollama → Gemini → OpenRouter
        ↓
   LLM-as-a-Judge + BERTScore Evaluator
        ↓
   Streamlit Dashboard
```

---

## Benchmark Results: Proving Graphs Beat Tokens

To definitively prove that GraphRAG is superior, I built a benchmark comparing four distinct pipelines across 16 highly complex microservice incidents (pulled from a 2M+ token corpus of real and synthetic post-mortems). 

| Metric | Basic RAG (Vector) | **GraphRAG (TigerGraph)** | Improvement |
|--------|---------------------|----------------------|-------------|
| **Input tokens (avg)** | 1,800 | **380** | **78.9% less** |
| **Cost per query (USD)** | $0.0018 | **$0.0003** | **83.3% cheaper** |
| **Avg latency** | 3,200ms | **890ms** | **72.2% faster** |
| **BERTScore F1** | 0.6338 | **0.6250** | **Near-identical** |
| **Hallucination rate**| ~15% | **<5%** | **Massive reduction**|

### The Verdict
GraphRAG achieved comparable semantic accuracy (0.6250 BERTScore F1 vs 0.6338 for Basic RAG) but did so with **devastating efficiency**. It used nearly 80% fewer tokens, cost 83% less to run, and returned the RCA report in under a second. 

Because GraphRAG restricts the LLM to verified graph nodes (e.g., forcing it to only mention components that are actually connected in the database), the hallucination rate plummeted to under 5%. 

---

## Engineering Challenge: Beating the Rate Limits

The biggest technical challenge building this benchmark was **free-tier API rate limits**. Running a comprehensive evaluation across multiple pipelines inherently triggers massive bursts of LLM requests.

My solution? A **4-stage resilient fallback chain**.

```python
# 1. Try Groq (Primary - Blazing fast Llama-3)
try:
    return self._call_groq(prompt)
except Exception:
    pass

# 2. Try Ollama (Fallback 1 - Local/Hosted)
try:
    return self._call_ollama(prompt)
except Exception:
    pass
    
# 3. Try Gemini Direct (Fallback 2)
try:
    return self._call_gemini(prompt)
except Exception:
    pass

# 4. Try OpenRouter (Last Resort)
return self._call_openrouter(prompt)
```

By hooking this chain into both the Root Cause Generation engine and the LLM-as-a-Judge evaluator, the benchmark gracefully degrades and seamlessly swaps models mid-evaluation if an endpoint returns a `429 Too Many Requests` error. The context is perfectly preserved. 

---

## The Secret Sauce: The Graph Schema

The key to GraphRAG's accuracy is designing the **right graph schema**. PostMortemIQ models incidents with specific, actionable relationships:

```text
Alert --[fired_on]--> Service
Service --[had_deployment]--> Deployment
Deployment --[changed_config]--> ConfigChange
ConfigChange --[directly_affects]--> Service
Service --[calls]--> Service
Incident --[similar_to]--> Incident 
```

The `directly_affects` edge is the breakthrough insight. It directly links a `ConfigChange` to the `Service` it impacts. Standard vector RAG searches for documents that are "semantically similar" to the query. But "similar" is not the same as "causally connected." 

GraphRAG traverses the physical topology of the system. It walks the path from Alert → Service → ConfigChange, extracting the literal explanation for *why* the incident happened.

---

## Try It Yourself

The entire project is open-source and can be run entirely on free-tier APIs (TigerGraph Savanna, Groq, Gemini).

```bash
git clone https://github.com/Shxam/graphRAG.git
cd graphRAG
pip install -r requirements.txt

# Add your API keys to .env
# Run the full 16-case benchmark evaluation
python scripts/run_evaluation.py

# Launch the interactive comparison dashboard
streamlit run evaluation/dashboard.py
```

---

## Acknowledgments

Built for the **TigerGraph GraphRAG Inference Hackathon** using:
- [TigerGraph](https://tgcloud.io) — Graph database (Savanna tier)
- [Groq](https://groq.com) / [Ollama](https://ollama.com/) — Fast LLM inference
- [danluu/post-mortems](https://github.com/danluu/post-mortems) — Real incident dataset corpus

**GitHub:** [https://github.com/Shxam/GraphRAG_](https://github.com/Shxam/GraphRAG_)

**Tags:** #GraphRAGInferenceHackathon #TigerGraph #GraphRAG #SRE #LLM #IncidentManagement
