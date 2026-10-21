"""
Mobile PWA-ready Streamlit UI for Sports Props Analyzer.
Can be installed to home screen on iPhone/Android.
"""
import streamlit as st
import os
from dotenv import load_dotenv
from data.data_fetcher import DataFetcher
from analysis.analyzer import PropAnalyzer
from analysis.parlay_builder import ParlayBuilder
from models.models import Sport

load_dotenv()

st.set_page_config(
    page_title="Props Analyzer",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# PWA / mobile meta
st.markdown("""
<link rel="manifest" href="data:application/json,{
  "name": "Sports Props Analyzer",
  "short_name": "Props",
  "start_url": ".",
  "display": "standalone",
  "background_color": "#0e1117",
  "theme_color": "#ff4b4b"
}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Props">
<style>
    .stApp { max-width: 480px; margin: 0 auto; }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    h1 { font-size: 1.6rem !important; text-align: center; }
    .stButton > button { 
        width: 100%; 
        border-radius: 12px; 
        height: 48px;
        font-weight: 600;
    }
    div[data-testid="stMetric"] {
        background: #1a1a1a;
        padding: 8px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Props Analyzer")
st.caption("PrizePicks · Underdog · Sleeper")

# Controls
sport = st.selectbox("Sport", [s.value for s in Sport])
min_edge = st.slider("Minimum edge", 0.0, 0.4, 0.05, 0.05)

if st.button("Load Props", type="primary"):
    st.session_state.load = True

if not os.getenv("ODDS_API_KEY"):
    st.error("Missing API key. Add ODDS_API_KEY to secrets or .env")
    st.stop()

fetcher = DataFetcher()
analyzer = PropAnalyzer()
builder = ParlayBuilder()

if st.session_state.get("load", False) or True:
    with st.spinner("Loading live props..."):
        props = fetcher.get_player_props(Sport(sport))
        analyzed = analyzer.analyze(props)

    top = [p for p in analyzed if (p.edge_score or 0) >= min_edge][:15]

    st.subheader("Top Props")
    if not top:
        st.info("Lower the edge slider to see more.")
    else:
        for i, p in enumerate(top, 1):
            best = p.best_line("over")
            with st.container(border=True):
                st.markdown(f"**{i}. {p.player.name}**")
                st.caption(f"{p.player.team or ''} · {p.market.value}")
                c1, c2, c3 = st.columns(3)
                if best:
                    c1.metric("Line", f"{best.line}")
                c2.metric("Edge", f"{(p.edge_score or 0):.2f}")
                hit = p.hit_rate_last_10
                if hit is not None:
                    c3.metric("Hit", f"{hit:.0%}")

    st.subheader("Parlays")
    parlays = builder.build_parlays(analyzed, min_edge=min_edge)
    if parlays:
        for parl in parlays[:4]:
            with st.expander(f"{parl.size}-leg · {parl.total_edge:.2f} edge"):
                for leg in parl.legs:
                    st.write(f"• {leg.prop.player.name} {leg.direction} {leg.line}")
    else:
        st.caption("No parlays above threshold.")
