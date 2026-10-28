"""Flame in Freefall - fire safety insights from NASA microgravity combustion data.

Run with:  streamlit run app.py
"""
import os

import plotly.graph_objects as go
import streamlit as st

from flame import assistant
from flame.data import load_dataset, load_habitats, to_dataframe
from flame.ranking import DEFAULT_WEIGHTS, coverage_gaps, rank
from flame.search import SearchIndex

st.set_page_config(page_title="Flame in Freefall", layout="wide")

# Copy keys from .streamlit/secrets.toml (or Streamlit Cloud secrets) into the environment for the assistant.
try:
    for key in ("GEMINI_API_KEY", "GEMINI_MODEL"):
        if key in st.secrets:
            os.environ.setdefault(key, st.secrets[key])
except Exception:  # no secrets file: offline mode
    pass


@st.cache_resource
def load():
    records, resources = load_dataset()
    return records, resources, load_habitats(), to_dataframe(records), SearchIndex(records, resources["documents"])


records, resources, habitats, df, index = load()
by_id = {r["id"]: r for r in records}

# ---------- Sidebar: mission profile ----------
st.sidebar.header("Mission profile")
habitat = st.sidebar.selectbox("Target habitat", habitats, index=2, format_func=lambda h: h["name"])
st.sidebar.caption(f"{habitat['o2_pct']}% O2 · {habitat['pressure_psi']} psi · {habitat['gravity_g']} g  \n{habitat['notes']}")

st.sidebar.subheader("Fire safety priority")
priorities = {
    "prevention": st.sidebar.slider("Prevention (flammability)", 0, 3, 3),
    "detection": st.sidebar.slider("Detection (smoke)", 0, 3, 1),
    "suppression": st.sidebar.slider("Suppression (extinguishing)", 0, 3, 2),
}
with st.sidebar.expander("Ranking weights"):
    weights = {k: st.slider(k.capitalize(), 0.0, 1.0, v, 0.05) for k, v in DEFAULT_WEIGHTS.items()}

st.sidebar.markdown("---")
st.sidebar.caption(f"AI assistant: {'Gemini (online)' if assistant.ai_available() else 'offline mode'}")
st.sidebar.caption(f"Resources: {len(resources['tests'])} test rows · {len(resources['documents'])} text passages "
                   f"· {len(resources['skipped'])} skipped")
if st.sidebar.button("Reload data/resources"):
    st.cache_resource.clear()
    st.rerun()
st.sidebar.caption("Note: seed dataset; condition values are approximate until replaced with NASA PSI data.")

# ---------- Header ----------
st.title("Flame in Freefall")
st.write("Rank, compare and interpret NASA microgravity combustion investigations for crew fire safety.")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Investigations", len(records))
c2.metric("Hardware platforms", df["hardware"].nunique())
c3.metric("Max O2 tested", f"{df['o2_max'].max():g}%")
c4.metric("Partial-g tests", 0, help="No partial-gravity data in PSI yet; ACME E-FIELD mimics buoyancy.")

tab_rank, tab_map, tab_compare, tab_ask, tab_data = st.tabs(
    ["Rank", "Atmosphere gaps", "Compare", "Ask", "Data"])

# ---------- Rank ----------
with tab_rank:
    st.subheader(f"Most relevant investigations for: {habitat['name']}")
    ranked = rank(records, habitat, priorities, weights)
    st.dataframe(
        ranked, hide_index=True, width="stretch",
        column_config={"score": st.column_config.ProgressColumn("score", min_value=0, max_value=1, format="%.2f")},
    )
    st.caption("score = weighted sum of pillar fit, atmosphere fit, fuel relevance and gravity fit (each 0–1). "
               "Adjust in the sidebar.")
    top = by_id[ranked.iloc[0]["id"]]
    with st.expander(f"Top pick: {top['name']}", expanded=True):
        st.write(top["objective"])
        for f in top["key_findings"]:
            st.markdown(f"- {f}")

# ---------- Atmosphere map ----------
with tab_map:
    st.subheader("Tested oxygen / pressure envelopes vs crew atmospheres")
    fig = go.Figure()
    colors = {"solid": "#d62728", "liquid": "#1f77b4", "gas": "#2ca02c", "smoke": "#7f7f7f", "dust": "#bcbd22"}
    for r in records:
        # Pad every box slightly so single-condition tests (zero-width ranges) are still visible.
        (o_lo, o_hi), (p_lo, p_hi) = r["conditions"]["o2_pct"], r["conditions"]["pressure_psi"]
        o_lo, o_hi, p_lo, p_hi = o_lo - 0.5, o_hi + 0.5, p_lo - 0.2, p_hi + 0.2
        fig.add_trace(go.Scatter(
            x=[o_lo, o_hi, o_hi, o_lo, o_lo], y=[p_lo, p_lo, p_hi, p_hi, p_lo], fill="toself",
            mode="lines", opacity=0.35, line=dict(color=colors.get(r["fuel_phase"], "#9467bd")), name=r["id"],
            legendgroup=r["fuel_phase"], hovertemplate=f"{r['id']} ({r['fuel_phase']})<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=[h["o2_pct"] for h in habitats], y=[h["pressure_psi"] for h in habitats],
        mode="markers+text", text=[h["name"] for h in habitats], textposition="top center",
        marker=dict(symbol="star", size=16, color="black"), name="Crew atmospheres"))
    fig.update_layout(xaxis_title="Oxygen (% by volume)", yaxis_title="Pressure (psi)", height=550,
                      xaxis=dict(range=[10, 105]), yaxis=dict(range=[0, 46]))
    st.plotly_chart(fig, width="stretch")
    st.caption("Shaded boxes = approximate test envelopes (colour = fuel type). Stars = crew atmospheres.")

    st.markdown("**Coverage by fuel type** — 1.0 means at least one investigation tested that exact atmosphere.")
    gaps = coverage_gaps(records, habitats)
    st.dataframe(gaps.pivot(index="habitat", columns="fuel_phase", values="best_fit"), width="stretch")
    solid = gaps[(gaps.fuel_phase == "solid") & (gaps.habitat == habitat["name"])]
    if not solid.empty and solid.iloc[0]["best_fit"] < 1:
        st.warning(f"No solid-material test covers the {habitat['name']} atmosphere. "
                   "Cabin materials (fabrics, plastics) are the main fire load, so this is a key data gap.")

# ---------- Compare ----------
with tab_compare:
    picks = st.multiselect("Choose 2–4 investigations", list(by_id), default=["BASS-II", "Saffire-I", "FLEX"],
                           max_selections=4)
    if picks:
        fields = ["name", "hardware", "year", "fuel_phase", "fuels", "o2_min", "o2_max", "p_min_psi",
                  "p_max_psi", "flow_min_cm_s", "flow_max_cm_s", "diluents", "measurements"]
        st.dataframe(df.set_index("id").loc[picks, fields].T.astype(str), width="stretch")

        axes = ["prevention", "detection", "suppression", "partial_gravity"]
        radar = go.Figure()
        for p in picks:
            vals = df.set_index("id").loc[p, axes].tolist()
            radar.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=axes + axes[:1], fill="toself", name=p))
        radar.update_layout(polar=dict(radialaxis=dict(range=[0, 3])), height=420)
        st.plotly_chart(radar, width="stretch")

        st.markdown("**Shared variables:** " + (", ".join(
            set.intersection(*(set(by_id[p].get("variables", [])) for p in picks))) or "none"))
        for p in picks:
            st.markdown(f"**{p}** — " + " ".join(by_id[p]["key_findings"]))

# ---------- Ask ----------
with tab_ask:
    st.subheader("Ask the data")
    examples = ["Which materials stay flammable at low ventilation speeds?",
                "What do we know about fires at high oxygen like a lunar base?",
                "How was smoke detection studied in microgravity?",
                "Which experiments studied extinguishing fires with CO2 or helium?"]
    question = st.text_input("Question", placeholder=examples[1])
    st.caption("Try: " + " · ".join(examples))
    if question:
        hits, doc_hits = index.search(question, k=5), index.search_docs(question, k=3)
        with st.spinner("Thinking..."):
            st.markdown(assistant.answer(question, hits, doc_hits))
        sources = [r["id"] for r, _ in hits] + [f"{d['title']} p{d['part']}" for d, _ in doc_hits]
        if sources:
            st.caption("Retrieved by hybrid search (BM25 + LSA, fused with RRF): " + ", ".join(sources))

# ---------- Data ----------
with tab_data:
    phases = st.multiselect("Fuel type", sorted(df.fuel_phase.unique()), default=sorted(df.fuel_phase.unique()))
    view = df[df.fuel_phase.isin(phases)]
    st.dataframe(view, hide_index=True, width="stretch")
    st.download_button("Download CSV", view.to_csv(index=False), "investigations.csv", "text/csv")
    with st.expander(f"Imported resources (data/resources/) — {len(resources['tests'])} test rows, "
                     f"{len({d['title'] for d in resources['documents']})} documents"):
        if not resources["tests"].empty:
            st.dataframe(resources["tests"], hide_index=True, width="stretch")
        for name, reason in resources["skipped"]:
            st.warning(f"Skipped {name}: {reason}")
        if resources["tests"].empty and not resources["documents"]:
            st.info("No resource files yet. Drop CSV / Excel / JSON / PDF / DOCX / TXT files into data/resources/ "
                    "and press Reload in the sidebar.")
    pick = st.selectbox("Details", list(by_id), format_func=lambda i: by_id[i]["name"])
    r = by_id[pick]
    st.markdown(f"**Objective:** {r['objective']}  \n**Geometry:** {r.get('sample_geometry', '-')}  \n"
                f"**Earth applications:** {', '.join(r.get('earth_applications', []))}")
    for f in r["key_findings"]:
        st.markdown(f"- {f}")
