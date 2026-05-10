import logging
import streamlit as st
import plotly.graph_objects as go
import fastf1 as ff1
import os

try:
    from src.logic import TelemetryEngine
except ModuleNotFoundError:
    from logic import TelemetryEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

os.makedirs("data", exist_ok=True)
ff1.Cache.enable_cache("data")

st.set_page_config(
    page_title="F1 Battle Engine",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Barlow+Condensed:wght@300;400;600;700&display=swap');

html, body, [class*="st-"] {
    font-family: 'DM Mono', monospace;
    background-color: #0a0a0a;
    color: #e8e4da;
}
.main { background-color: #0a0a0a; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

[data-testid="stSidebar"] { background-color: #111; border-right: 1px solid #222; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p {
    font-family: 'DM Mono', monospace;
    font-size: 11px; color: #666;
    text-transform: uppercase; letter-spacing: 0.08em;
}
[data-testid="stSidebar"] .stButton > button {
    background-color: #c8ff00; color: #0a0a0a; border: none; border-radius: 3px;
    font-family: 'Barlow Condensed', sans-serif; font-weight: 700;
    font-size: 15px; letter-spacing: 0.14em; padding: 12px; width: 100%; margin-top: 8px;
}
[data-testid="stSidebar"] .stButton > button:hover { background-color: #d9ff1a; }

.wordmark {
    font-family: 'Barlow Condensed', sans-serif; font-weight: 700;
    font-size: 13px; letter-spacing: 0.22em; color: #c8ff00; margin-bottom: 1.5rem;
}
.page-header {
    border-bottom: 1px solid #1e1e1e; padding-bottom: 1rem;
    margin-bottom: 1.5rem; display: flex; align-items: baseline; gap: 1.5rem;
}
.page-title {
    font-family: 'Barlow Condensed', sans-serif; font-size: 42px;
    font-weight: 700; letter-spacing: -0.5px; color: #f0ece0; line-height: 1;
}
.page-meta { font-size: 11px; color: #444; letter-spacing: 0.06em; }

.stat-strip {
    display: grid; grid-template-columns: repeat(5, 1fr);
    gap: 1px; background: #1a1a1a; border: 1px solid #1a1a1a;
    border-radius: 4px; margin-bottom: 1.5rem;
}
.stat-cell { background: #0a0a0a; padding: 14px 18px; }
.stat-label { font-size: 9px; color: #444; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px; }
.stat-value { font-family: 'Barlow Condensed', sans-serif; font-size: 26px; font-weight: 600; color: #f0ece0; line-height: 1; }
.stat-unit { font-size: 10px; color: #555; margin-left: 3px; }
.stat-accent-1 { color: #4fc3f7; }
.stat-accent-2 { color: #ff7043; }
.stat-accent-delta { color: #c8ff00; }

.section-label {
    font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase;
    color: #444; margin-bottom: 8px; margin-top: 1.5rem;
}
.sector-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.sector-table th {
    color: #444; font-size: 9px; letter-spacing: 0.12em; text-transform: uppercase;
    text-align: left; padding: 6px 10px; border-bottom: 1px solid #1e1e1e; font-weight: 400;
}
.sector-table td { padding: 7px 10px; border-bottom: 1px solid #141414; color: #c0baa8; font-variant-numeric: tabular-nums; }
.sector-table tr:hover td { background: #111; }
.gain { color: #c8ff00; }
.loss { color: #ff5252; }
.status-bar {
    font-size: 10px; color: #333; letter-spacing: 0.08em;
    border-top: 1px solid #1a1a1a; padding-top: 10px; margin-top: 2rem;
    display: flex; justify-content: space-between;
}
.idle-wrap {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: 65vh; gap: 16px; text-align: center;
}
.idle-glyph { font-size: 56px; color: #1c1c1c; line-height: 1; font-family: 'Barlow Condensed', sans-serif; }
.idle-title { font-family: 'Barlow Condensed', sans-serif; font-size: 22px; font-weight: 600; color: #2a2a2a; }
.idle-sub { font-size: 11px; color: #2a2a2a; letter-spacing: 0.16em; text-transform: uppercase; }
.error-block {
    background: rgba(255,82,82,0.08); border: 1px solid rgba(255,82,82,0.2);
    border-radius: 4px; padding: 16px; font-size: 12px; color: #ff5252;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Session State Init ────────────────────────────────────────────────────────
if "cached_result" not in st.session_state:
    st.session_state.cached_result = None
if "cached_params" not in st.session_state:
    st.session_state.cached_params = None

# ── Dynamic loaders ───────────────────────────────────────────────────────────
AVAILABLE_YEARS = list(range(2024, 2017, -1))

@st.cache_data(show_spinner=False)
def get_circuits(year: int):
    try:
        sched = ff1.get_event_schedule(year, include_testing=False)
        return sched["EventName"].tolist()
    except Exception:
        return []

@st.cache_data(show_spinner=False)
def get_drivers(year: int, gp: str, session_type: str):
    try:
        sess = ff1.get_session(year, gp, session_type)
        sess.load(laps=True, telemetry=False, weather=False)
        return sorted(sess.laps["Driver"].dropna().unique().tolist())
    except Exception:
        return []

@st.cache_resource
def get_engine(n_sectors: int):
    """Cache engine instance to avoid reinit."""
    return TelemetryEngine(n_sectors=n_sectors)

FALLBACK_DRIVERS = ["ALB","ALO","BOT","GAS","HAM","HUL","LEC","MAG",
                    "NOR","OCO","PER","PIA","RUS","SAI","STR","TSU","VER","ZHO"]

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="wordmark">⬡ BATTLE ENGINE</div>', unsafe_allow_html=True)

    st.markdown("Season")
    year = st.selectbox("Season", AVAILABLE_YEARS, label_visibility="collapsed")

    st.markdown("Circuit")
    with st.spinner("Loading schedule…"):
        circuits = get_circuits(year) or ["Silverstone", "Monaco", "Spa", "Monza"]
    gp = st.selectbox("Circuit", circuits, label_visibility="collapsed")

    st.markdown("Session")
    session_label = st.selectbox("Session", ["Qualifying", "Race", "Sprint"], label_visibility="collapsed")
    s_key = {"Qualifying": "Q", "Race": "R", "Sprint": "S"}[session_label]

    st.markdown("&nbsp;", unsafe_allow_html=True)
    st.markdown("Drivers")
    auto_drivers = st.checkbox("Load actual grid", value=False,
                               help="Queries FastF1 for the real driver list — adds ~5s")
    if auto_drivers:
        with st.spinner("Fetching driver list…"):
            driver_list = get_drivers(year, gp, s_key) or FALLBACK_DRIVERS
    else:
        driver_list = FALLBACK_DRIVERS

    d1 = st.selectbox("Driver 1", driver_list,
                      index=driver_list.index("HAM") if "HAM" in driver_list else 0,
                      label_visibility="collapsed")
    d2 = st.selectbox("Driver 2", driver_list,
                      index=driver_list.index("VER") if "VER" in driver_list else min(1, len(driver_list)-1),
                      label_visibility="collapsed")

    n_sectors = st.slider("Mini-sectors", 10, 30, 20)
    st.markdown("&nbsp;", unsafe_allow_html=True)
    run_btn = st.button("▶  RUN ANALYSIS", use_container_width=True)

# ── PLOT THEME ────────────────────────────────────────────────────────────────
LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d0d0d",
    font=dict(family="DM Mono, monospace", size=10, color="#555"),
    margin=dict(l=44, r=10, t=10, b=30),
    xaxis=dict(gridcolor="#161616", linecolor="#1e1e1e", tickcolor="#333", zeroline=False),
    yaxis=dict(gridcolor="#161616", linecolor="#1e1e1e", tickcolor="#333", zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(size=10)),
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#111", bordercolor="#333", font=dict(family="DM Mono", size=11)),
)
C1, C2, CD = "#4fc3f7", "#ff7043", "#c8ff00"

def make_layout(**overrides):
    lay = dict(LAYOUT_BASE)
    for k, v in overrides.items():
        if k in ("xaxis", "yaxis"):
            lay[k] = {**LAYOUT_BASE.get(k, {}), **v}
        else:
            lay[k] = v
    return lay

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="page-header">
  <div class="page-title">{gp.upper()} {year}</div>
  <div class="page-meta">{session_label.upper()} · {d1} vs {d2}</div>
</div>
""", unsafe_allow_html=True)

# ── MAIN ──────────────────────────────────────────────────────────────────────
if run_btn:
    current_params = (year, gp, s_key, d1, d2, n_sectors)
    
    # Check if results are cached
    if st.session_state.cached_result and st.session_state.cached_params == current_params[:-1]:
        result = st.session_state.cached_result
        st.success("✓ Using cached results", icon="✓")
    else:
        # Run analysis with progress tracking
        progress_bar = st.progress(0, text="Loading session…")
        
        try:
            progress_bar.progress(20, text="Loading session data…")
            engine = get_engine(n_sectors)
            
            progress_bar.progress(40, text="Computing telemetry…")
            result = engine.compare(year, gp, s_key, d1, d2)
            
            progress_bar.progress(80, text="Finalizing…")
            
            # Cache the result
            st.session_state.cached_result = result
            st.session_state.cached_params = current_params[:-1]
            
            progress_bar.progress(100, text="Complete!")
            
        except Exception as e:
            progress_bar.empty()
            st.markdown(f'<div class="error-block">ERR · {e}</div>', unsafe_allow_html=True)
            st.stop()

    data = result.telemetry
    sectors = result.sectors
    s = result.summary

    delta_end = s["cumulative_delta_s"]
    delta_sign = "+" if delta_end > 0 else ""
    _lat_vals = [v for v in [s["max_lat_g"][d1], s["max_lat_g"][d2]] if v is not None]
    _peak_lat = f"{max(_lat_vals):.2f}" if _lat_vals else "—"

    st.markdown(f"""
    <div class="stat-strip">
      <div class="stat-cell">
        <div class="stat-label">Lap · {d1}</div>
        <div class="stat-value stat-accent-1">{s['lap_times'][d1]}</div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">Lap · {d2}</div>
        <div class="stat-value stat-accent-2">{s['lap_times'][d2]}</div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">Top speed</div>
        <div class="stat-value">{max(s['top_speed'][d1], s['top_speed'][d2]):.0f}<span class="stat-unit">km/h</span></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">Peak lat G</div>
        <div class="stat-value">{_peak_lat}<span class="stat-unit">G</span></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">End Δ</div>
        <div class="stat-value stat-accent-delta">{delta_sign}{delta_end:.3f}<span class="stat-unit">s</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Use tabs for chart sections (lazy loading)
    tab1, tab2, tab3, tab4 = st.tabs(["Velocity & Delta", "G-Forces", "Pedals", "Sectors"])

    with tab1:
        st.markdown('<div class="section-label">Velocity &amp; time delta</div>', unsafe_allow_html=True)
        col_v, col_d = st.columns([3, 2])
        with col_v:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data["Distance"], y=data[f"Speed_smooth_{d1}"],
                name=d1, line=dict(color=C1, width=1.8), hovertemplate="%{y:.1f} km/h"))
            fig.add_trace(go.Scatter(x=data["Distance"], y=data[f"Speed_smooth_{d2}"],
                name=d2, line=dict(color=C2, width=1.8), hovertemplate="%{y:.1f} km/h"))
            fig.update_layout(**make_layout(yaxis={"title": "km/h"}, xaxis={"title": "distance (m)"}, height=280))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with col_d:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=data["Distance"], y=data["Delta"],
                fill="tozeroy", fillcolor="rgba(200,255,0,0.07)",
                line=dict(color=CD, width=1.5), name="Δ", hovertemplate="%{y:.3f}s"))
            fig2.add_hline(y=0, line=dict(color="#2a2a2a", width=1))
            fig2.update_layout(**make_layout(yaxis={"title": "Δ s"}, xaxis={"title": "distance (m)"}, height=280))
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    with tab2:
        st.markdown('<div class="section-label">G-force traces</div>', unsafe_allow_html=True)
        col_gx, col_gy = st.columns(2)
        with col_gx:
            fg = go.Figure()
            fg.add_hline(y=0, line=dict(color="#222", width=1))
            fg.add_trace(go.Scatter(x=data["Distance"], y=data[f"Gx_{d1}"],
                name=d1, line=dict(color=C1, width=1.4), hovertemplate="%{y:.2f}G"))
            fg.add_trace(go.Scatter(x=data["Distance"], y=data[f"Gx_{d2}"],
                name=d2, line=dict(color=C2, width=1.4), hovertemplate="%{y:.2f}G"))
            fg.update_layout(**make_layout(yaxis={"title": "Gx (long.)"}, xaxis={"title": "distance (m)"}, height=240))
            st.plotly_chart(fg, use_container_width=True, config={"displayModeBar": False})
        with col_gy:
            has_gy = f"Gy_{d1}" in data.columns and data[f"Gy_{d1}"].notna().any()
            if has_gy:
                fg2 = go.Figure()
                fg2.add_hline(y=0, line=dict(color="#222", width=1))
                fg2.add_trace(go.Scatter(x=data["Distance"], y=data[f"Gy_{d1}"],
                    name=d1, line=dict(color=C1, width=1.4), hovertemplate="%{y:.2f}G"))
                fg2.add_trace(go.Scatter(x=data["Distance"], y=data[f"Gy_{d2}"],
                    name=d2, line=dict(color=C2, width=1.4), hovertemplate="%{y:.2f}G"))
                fg2.update_layout(**make_layout(yaxis={"title": "Gy (lat.)"}, xaxis={"title": "distance (m)"}, height=240))
                st.plotly_chart(fg2, use_container_width=True, config={"displayModeBar": False})
            else:
                st.markdown('<div style="color:#2a2a2a;font-size:11px;padding:80px 0;text-align:center;">X/Y unavailable — Gy not computed</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="section-label">Pedal traces</div>', unsafe_allow_html=True)
        has_thr = f"Throttle_{d1}" in data.columns and data[f"Throttle_{d1}"].notna().any()
        if has_thr:
            ct, cb = st.columns(2)
            with ct:
                ft = go.Figure()
                ft.add_trace(go.Scatter(x=data["Distance"], y=data[f"Throttle_{d1}"], name=d1, line=dict(color=C1, width=1.4)))
                ft.add_trace(go.Scatter(x=data["Distance"], y=data[f"Throttle_{d2}"], name=d2, line=dict(color=C2, width=1.4)))
                ft.update_layout(**make_layout(yaxis={"title": "Throttle %", "range": [0, 105]}, xaxis={"title": "distance (m)"}, height=200))
                st.plotly_chart(ft, use_container_width=True, config={"displayModeBar": False})
            with cb:
                fb = go.Figure()
                fb.add_trace(go.Scatter(x=data["Distance"], y=data[f"Brake_{d1}"], name=d1, line=dict(color=C1, width=1.4)))
                fb.add_trace(go.Scatter(x=data["Distance"], y=data[f"Brake_{d2}"], name=d2, line=dict(color=C2, width=1.4)))
                fb.update_layout(**make_layout(yaxis={"title": "Brake"}, xaxis={"title": "distance (m)"}, height=200))
                st.plotly_chart(fb, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Throttle/Brake data unavailable for this session")

    with tab4:
        st.markdown('<div class="section-label">Mini-sector breakdown</div>', unsafe_allow_html=True)
        # Use st.dataframe instead of HTML for better performance
        display_df = sectors.copy()
        display_df = display_df[[
            "Sector", "Dist_start", "Dist_end", 
            f"AvgSpeed_{d1}", f"AvgSpeed_{d2}",
            f"PeakBrake_{d1}", f"PeakBrake_{d2}",
            "Delta_gained"
        ]].round(2)
        display_df.columns = ["#", "Start (m)", "End (m)", f"Avg Spd {d1}", f"Avg Spd {d2}", 
                               f"Pk Brk {d1}", f"Pk Brk {d2}", "Δ gained (s)"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown(f"""
    <div class="status-bar">
      <span>{s['data_points']} pts · {n_sectors} sectors</span>
      <span>{d1}: {s['compounds'][d1]} · {d2}: {s['compounds'][d2]}</span>
      <span>FastF1 · MARS Engineering © 2026</span>
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown(f"""
    <div class="idle-wrap">
      <div class="idle-glyph">⬡</div>
      <div class="idle-title">{gp} {year} · {session_label}</div>
      <div class="idle-sub">{d1} &nbsp;vs&nbsp; {d2} &nbsp;·&nbsp; press ▶ run analysis in the sidebar</div>
    </div>
    """, unsafe_allow_html=True)