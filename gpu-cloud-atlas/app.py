import streamlit as st
from dotenv import load_dotenv
from atlas import data, llm

load_dotenv()
st.set_page_config(page_title="GPU Cloud Atlas", page_icon="🌍", layout="wide")
providers = data.load()

st.title("🌍 GPU Cloud Atlas")
st.caption("Which countries and companies run GPU servers, what hardware and models they offer, "
           "and their pros & cons. Curated dataset + LLM analyst. Verify figures before decisions.")

with st.sidebar:
    st.header("Filters")
    sel_c = st.multiselect("Country", data.countries(providers))
    sel_t = st.multiselect("Provider type", data.types(providers))
    gpu = st.text_input("GPU contains", placeholder="H100, B200, Ascend…")
    st.header("AI backend")
    backend = st.selectbox("Backend", ["auto"] + llm.available_backends())
    if llm.available_backends() == ["offline"]:
        st.info("No API key found: running offline. Copy .env.example to .env to enable AI.")

flt = data.filter_providers(providers, sel_c, sel_t, gpu)
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🗺️ Explore", "⚖️ Compare", "💬 Ask the Analyst", "📄 Country Report", "🔄 Live Refresh"])

with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Providers", len(flt))
    c2.metric("Countries", len({p["country"] for p in flt}))
    c3.metric("Hyperscalers", sum(p["type"] == "Hyperscaler" for p in flt))
    if flt:
        df = data.to_dataframe(flt)
        st.map(df[["lat", "lon"]])
        st.dataframe(df.drop(columns=["lat", "lon"]), use_container_width=True, hide_index=True)
        for p in flt:
            with st.expander(f"{p['name']} — {p['country']} ({p['type']})"):
                st.write(p["what_they_do"])
                a, b = st.columns(2)
                a.markdown("**GPUs:** " + ", ".join(p["gpus"]))
                a.markdown("**Capacity:** " + p["capacity"])
                a.markdown("**Resources:** " + ", ".join(p["resources"]))
                a.markdown("**Models:** " + ", ".join(p["models_offered"]))
                b.markdown("**✅ Pros**\n" + "\n".join(f"- {x}" for x in p["pros"]))
                b.markdown("**⚠️ Cons**\n" + "\n".join(f"- {x}" for x in p["cons"]))
                st.caption(f"Pricing: {p.get('pricing_note','n/a')} · Confidence: {p['confidence']} · "
                           f"[Website]({p.get('website','#')})")
    else:
        st.warning("No providers match these filters.")

with tab2:
    names = st.multiselect("Pick 2–3 providers", [p["name"] for p in providers], max_selections=3)
    if len(names) >= 2:
        cols = st.columns(len(names))
        for col, n in zip(cols, names):
            p = next(x for x in providers if x["name"] == n)
            col.subheader(p["name"]); col.caption(f"{p['country']} · {p['type']}")
            col.markdown("**GPUs:** " + ", ".join(p["gpus"]))
            col.markdown("**Capacity:** " + p["capacity"])
            col.markdown("**Models:** " + ", ".join(p["models_offered"]))
            col.markdown("**Pros**\n" + "\n".join(f"- {x}" for x in p["pros"]))
            col.markdown("**Cons**\n" + "\n".join(f"- {x}" for x in p["cons"]))
        if st.button("AI verdict: which fits which use-case?"):
            with st.spinner("Thinking…"):
                st.markdown(llm.ask(f"Compare {', '.join(names)} for training, inference and startups.",
                                    [p for p in providers if p["name"] in names], backend))
    else:
        st.info("Select at least two providers.")

with tab3:
    st.session_state.setdefault("msgs", [])
    for m in st.session_state.msgs:
        st.chat_message(m["role"]).markdown(m["content"])
    if q := st.chat_input("e.g. Which Indian providers offer H100s and what are the cons?"):
        st.chat_message("user").markdown(q)
        with st.spinner("Analysing…"):
            ans = llm.ask(q, providers, backend, st.session_state.msgs)
        st.chat_message("assistant").markdown(ans)
        st.session_state.msgs += [{"role": "user", "content": q}, {"role": "assistant", "content": ans}]

with tab4:
    country = st.selectbox("Country", data.countries(providers))
    if st.button("Generate briefing"):
        with st.spinner("Writing report…"):
            report = llm.country_report(country, providers, backend)
        st.markdown(report)
        st.download_button("Download .md", report, file_name=f"gpu-report-{country}.md")

with tab5:
    st.write("Fetch fresh public info with Claude web search (needs `ANTHROPIC_API_KEY`).")
    who = st.selectbox("Provider", [p["name"] for p in providers], key="live")
    if st.button("Search the web"):
        with st.spinner("Searching…"):
            st.markdown(llm.live_update(who))
