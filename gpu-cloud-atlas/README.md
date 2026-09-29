# 🌍 GPU Cloud Atlas

An AI-powered research app that answers: **which countries and companies run GPU servers, what hardware and capacity they have, what resources and models they offer, and what the pros and cons are.**

It combines a **curated, structured dataset** (27 providers across 13 countries) with an **LLM analyst** (Claude API or a free Groq/Llama API) that answers *only from the data* (RAG-lite), so it does not hallucinate GPU counts.

## Features

| Tab | What it does |
|---|---|
| 🗺️ Explore | Map + table + detail cards. Filter by country, provider type, GPU model (e.g. `H100`, `Ascend`) |
| ⚖️ Compare | Side-by-side comparison of 2–3 providers, plus an AI verdict per use-case |
| 💬 Ask the Analyst | Multi-turn chat, e.g. *"Which Indian providers offer H100s and what are the cons?"* |
| 📄 Country Report | One-click AI briefing for any country, downloadable as Markdown |
| 🔄 Live Refresh | Claude **web-search tool** fetches fresh public info to check stale data |

## Architecture

```
            ┌────────────────────────────┐
            │   Streamlit UI (app.py)    │
            └─────────────┬──────────────┘
                          │
      ┌───────────────────▼───────────────────┐
      │ atlas/data.py                          │
      │  load + validate → filter → retrieve   │  ← keyword scoring, demonym aliases
      └───────────────────┬───────────────────┘     (Indian→India), top-k context
                          │ context (JSON)
      ┌───────────────────▼───────────────────┐
      │ atlas/llm.py  (grounded prompting)     │
      │  Claude API │ Groq (free) │ Offline    │  ← auto-fallback if a call fails
      └────────────────────────────────────────┘
        data/providers.json  (single source of truth)
```

**Design decisions worth mentioning in interviews**
- **Grounded generation:** system prompt forces "answer only from DATA", flags low-confidence entries.
- **Graceful degradation:** no key → offline mode; API error → falls back to offline summary.
- **Provider abstraction:** swap Claude ↔ Llama without touching UI code.
- **Data-quality field:** each entry has `confidence` (high/medium/low); announced projects are marked as such.
- **Freshness:** Live Refresh tab uses Claude's web search to cross-check, instead of trusting a static snapshot.

## Quick start

```bash
git clone <your-repo-url> && cd gpu-cloud-atlas
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # add ONE key (optional)
streamlit run app.py
```

### API keys (pick any, or none)
| Option | Cost | Setup |
|---|---|---|
| Claude API | Paid | `ANTHROPIC_API_KEY` from console.anthropic.com. Also enables Live Refresh |
| Groq (Llama 3.3 70B) | Free tier | `GROQ_API_KEY` from console.groq.com |
| None | Free | Runs in offline mode (search/filter/compare still work) |

## Project structure

```
gpu-cloud-atlas/
├── app.py                # Streamlit UI
├── atlas/
│   ├── data.py           # load, validate, filter, retrieve
│   └── llm.py            # Claude / Groq / offline + web-search refresh
├── data/providers.json   # dataset
├── tests/test_data.py    # pytest suite
├── requirements.txt
└── .env.example
```

## Dataset schema

`id, name, country, hq_city, lat, lon, type, what_they_do, gpus[], capacity, resources[], models_offered[], pros[], cons[], pricing_note, website, confidence`

To add a provider, append an object to `data/providers.json`. `load()` validates required fields on startup.

## Testing

```bash
python -m pytest -q
```

## ⚠️ Limitations and honesty notes

- The dataset is a **snapshot compiled from public information and may be out of date**. GPU counts are approximate; entries marked `low` confidence are announcements or estimates. **Verify before making purchasing or investment decisions.**
- Pricing is intentionally qualitative (Budget / Mid / Premium) because cloud prices change often.
- Retrieval is keyword-based; with a larger dataset, swap in embeddings + a vector store.

## Roadmap
- [ ] Embedding-based retrieval (sentence-transformers + FAISS)
- [ ] Pricing scraper with a scheduled refresh (GitHub Actions)
- [ ] Structured-output extraction to auto-propose dataset updates from Live Refresh
- [ ] Docker image + Streamlit Community Cloud deploy
- [ ] Add more regions (Korea, Brazil, Australia, Nordics)

## License
MIT
