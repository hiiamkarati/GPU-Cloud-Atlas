"""LLM layer: Claude API, Groq (free tier, Llama), or offline fallback."""
from __future__ import annotations
import json, os
import requests
from . import data

SYSTEM = (
    "You are GPU Cloud Atlas, an analyst of global GPU / AI compute infrastructure. "
    "Answer ONLY from the provided DATA (JSON). If the data does not contain the answer, say so "
    "and suggest verifying on the provider's website. Never invent GPU counts or prices. "
    "Entries with confidence 'low' are announced/estimated: flag them as such. "
    "Be concise, structured, and use short bullet lists or comparison tables when useful."
)


def available_backends() -> list[str]:
    b = []
    if os.getenv("ANTHROPIC_API_KEY"): b.append("claude")
    if os.getenv("GROQ_API_KEY"): b.append("groq")
    return b + ["offline"]


def _pick(backend: str) -> str:
    avail = available_backends()
    return avail[0] if backend == "auto" or backend not in avail else backend


def _claude(system: str, messages: list[dict], tools=None) -> str:
    import anthropic
    client = anthropic.Anthropic()
    kwargs = dict(model=os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"),
                  max_tokens=1500, system=system, messages=messages)
    if tools: kwargs["tools"] = tools
    resp = client.messages.create(**kwargs)
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()


def _groq(system: str, messages: list[dict]) -> str:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={"model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
              "messages": [{"role": "system", "content": system}] + messages,
              "temperature": 0.2, "max_tokens": 1500},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def offline_answer(providers: list[dict]) -> str:
    if not providers: return "No matching providers found."
    lines = ["**Offline mode** (add an API key for AI analysis). Matching providers:\n"]
    for p in providers:
        lines.append(f"- **{p['name']}** ({p['country']}): {p['what_they_do']} "
                     f"GPUs: {', '.join(p['gpus'])}. Capacity: {p['capacity']}.")
    return "\n".join(lines)


def ask(question: str, providers: list[dict], backend: str = "auto",
        history: list[dict] | None = None) -> str:
    ctx = data.retrieve(providers, question)
    backend = _pick(backend)
    if backend == "offline":
        return offline_answer(ctx)
    prompt = f"DATA:\n{json.dumps(data.compact(ctx), ensure_ascii=False)}\n\nQUESTION: {question}"
    msgs = [{"role": m["role"], "content": m["content"]} for m in (history or [])[-6:]]
    msgs.append({"role": "user", "content": prompt})
    try:
        return _claude(SYSTEM, msgs) if backend == "claude" else _groq(SYSTEM, msgs)
    except Exception as e:  # network, auth, rate limit
        return f"⚠️ {backend} call failed ({type(e).__name__}: {e}).\n\n" + offline_answer(ctx)


def country_report(country: str, providers: list[dict], backend: str = "auto") -> str:
    subset = [p for p in providers if p["country"] == country]
    q = (f"Write a briefing on the GPU cloud landscape in {country}: key players, hardware, "
         "capacity, models supported, strengths/weaknesses, and who should use which.")
    return ask(q, subset, backend)


def live_update(provider_name: str) -> str:
    """Use Claude's web-search tool to fetch fresh news (Claude backend only)."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return "Live refresh needs ANTHROPIC_API_KEY (uses Claude web search)."
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]
    msg = [{"role": "user", "content": (
        f"Search for the latest verified info on {provider_name}'s GPU capacity, hardware, "
        "and any recent announcements. Reply with 5 short bullets and list source names.")}]
    try:
        return _claude("You are a careful research assistant. Only report what sources state.", msg, tools)
    except Exception as e:
        return f"Live refresh failed: {type(e).__name__}: {e}"
