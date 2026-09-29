"""Dataset loading, filtering and lightweight retrieval (RAG-lite)."""
from __future__ import annotations
import json, re
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "providers.json"
REQUIRED = {"id", "name", "country", "type", "what_they_do", "gpus", "capacity",
            "resources", "models_offered", "pros", "cons", "lat", "lon", "confidence"}
ALIASES = {"indian": "india", "french": "france", "german": "germany", "japanese": "japan",
           "chinese": "china", "emirati": "emirates", "saudi": "saudi", "canadian": "canada",
           "british": "kingdom", "uk": "kingdom", "american": "states", "usa": "states",
           "us": "states", "uae": "emirates", "dutch": "netherlands", "african": "africa"}
STOP = {"the", "and", "for", "with", "which", "what", "who", "how", "are", "has", "have",
        "does", "do", "of", "in", "a", "an", "to", "is", "me", "tell", "show", "about"}


def load(path: Path = DATA_PATH) -> list[dict]:
    providers = json.loads(Path(path).read_text(encoding="utf-8"))
    for p in providers:
        missing = REQUIRED - p.keys()
        if missing:
            raise ValueError(f"{p.get('name', '?')} missing fields: {sorted(missing)}")
    return providers


def countries(providers): return sorted({p["country"] for p in providers})
def types(providers): return sorted({p["type"] for p in providers})


def filter_providers(providers, countries=None, types=None, gpu="", text=""):
    out = []
    for p in providers:
        if countries and p["country"] not in countries: continue
        if types and p["type"] not in types: continue
        if gpu and not any(gpu.lower() in g.lower() for g in p["gpus"]): continue
        if text and text.lower() not in json.dumps(p).lower(): continue
        out.append(p)
    return out


def _tokens(q: str) -> list[str]:
    toks = [t for t in re.split(r"[^a-z0-9]+", q.lower()) if t and t not in STOP]
    return [ALIASES.get(t, t) for t in toks]


def retrieve(providers, query: str, k: int = 8) -> list[dict]:
    """Keyword-score providers against a query. Falls back to all providers."""
    toks = _tokens(query)
    scored = []
    for p in providers:
        head = f"{p['name']} {p['country']} {p['hq_city']}".lower()
        body = json.dumps(p).lower()
        s = sum(5 for t in toks if t in head) + sum(body.count(t) for t in toks)
        scored.append((s, p))
    scored.sort(key=lambda x: -x[0])
    if not scored or scored[0][0] == 0:
        return providers
    return [p for s, p in scored[:k] if s > 0]


def compact(providers) -> list[dict]:
    """Strip fields the LLM does not need (saves tokens)."""
    drop = {"lat", "lon", "id"}
    return [{k: v for k, v in p.items() if k not in drop} for p in providers]


def to_dataframe(providers):
    import pandas as pd
    return pd.DataFrame([{
        "Provider": p["name"], "Country": p["country"], "Type": p["type"],
        "GPUs": ", ".join(p["gpus"]), "Capacity": p["capacity"],
        "Pricing": p.get("pricing_note", ""), "Confidence": p["confidence"],
        "lat": p["lat"], "lon": p["lon"]} for p in providers])
