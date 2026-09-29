from atlas import data, llm

P = data.load()

def test_dataset_valid():
    assert len(P) >= 25
    assert len({p["id"] for p in P}) == len(P)
    assert all(p["pros"] and p["cons"] and p["gpus"] for p in P)

def test_filter():
    assert all(p["country"] == "India" for p in data.filter_providers(P, countries=["India"]))
    assert all(any("h100" in g.lower() for g in p["gpus"]) for p in data.filter_providers(P, gpu="H100"))

def test_retrieve_country_alias():
    assert data.retrieve(P, "Indian GPU cloud with H100", k=3)[0]["country"] == "India"

def test_retrieve_fallback_returns_all():
    assert len(data.retrieve(P, "zzzz qqqq")) == len(P)

def test_offline_ask(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "GROQ_API_KEY"): monkeypatch.delenv(k, raising=False)
    assert "Yotta" in llm.ask("Tell me about Indian GPU providers", P)

def test_dataframe():
    assert len(data.to_dataframe(P)) == len(P)
