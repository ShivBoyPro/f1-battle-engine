import logging
import streamlit as st
import plotly.graph_objects as go
import fastf1 as ff1
import os

# --- LOGIC IMPORT ---
try:
    from src.logic import TelemetryEngine
except ModuleNotFoundError:
    from logic import TelemetryEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- CACHE SETUP ---
os.makedirs("data", exist_ok=True)
ff1.Cache.enable_cache("data")

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="F1 Battle Engine",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLING ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Barlow+Condensed:wght@300;400;600;700&display=swap');

html, body, .stApp {
    font-family: 'DM Mono', monospace;
    background-color: #0a0a0a;
    color: #e8e4da;
}
.main { background-color: #0a0a0a; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* --- HEADER FIXES --- */
/* Hide the deploy button and main menu */
[data-testid="stHeaderActionButton"] { display: none !important; }
#MainMenu { display: none !important; }
footer { visibility: hidden; }

/* Keep header transparent */
header { background-color: transparent !important; }

/* Force Material icon font back onto the header elements so it renders an icon instead of 'keyboard_double' text */
header span {
    font-family: "Material Symbols Rounded", sans-serif !important;
    color: #666 !important;
}
header span:hover {
    color: #c8ff00 !important;
}

/* --- SIDEBAR --- */
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

.wordmark-container {
    display: flex; align-items: center; gap: 8px; margin-bottom: 1.5rem;
}
.wordmark {
    font-family: 'Barlow Condensed', sans-serif; font-weight: 700;
    font-size: 13px; letter-spacing: 0.22em; color: #c8ff00;
}

/* --- TYPOGRAPHY & LAYOUT --- */
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
    justify-content: center; min-height: 100vh; gap: 24px; text-align: center;
}
.idle-title { font-family: 'Barlow Condensed', sans-serif; font-size: 48px; font-weight: 600; color: #f0ece0; letter-spacing: -1px; }
.idle-sub { font-size: 13px; color: #666; letter-spacing: 0.16em; text-transform: uppercase; }
.error-block {
    background: rgba(255,82,82,0.08); border: 1px solid rgba(255,82,82,0.2);
    border-radius: 4px; padding: 16px; font-size: 12px; color: #ff5252;
}
</style>
""", unsafe_allow_html=True)

# --- DATA HELPERS ---
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

FALLBACK_DRIVERS = ["ALB","ALO","BOT","GAS","HAM","HUL","LEC","MAG",
                    "NOR","OCO","PER","PIA","RUS","SAI","STR","TSU","VER","ZHO"]

# --- SIDEBAR ---
with st.sidebar:
    # Sidebar Icon + Wordmark
    st.markdown("""
        <div class="wordmark-container">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#c8ff00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path>
            </svg>
            <span class="wordmark">BATTLE ENGINE</span>
        </div>
    """, unsafe_allow_html=True)

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
    auto_drivers = st.checkbox("Load actual grid", value=False)
    
    if auto_drivers:
        with st.spinner("Fetching grid…"):
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

# --- PLOT THEME ---
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

# --- MAIN EXECUTION ---
if run_btn:
    with st.spinner(f"Loading {gp} {year} {session_label}..."):
        try:
            engine = TelemetryEngine(n_sectors=n_sectors)
            result  = engine.compare(year, gp, s_key, d1, d2)
            data    = result.telemetry
            sectors = result.sectors
            s       = result.summary
        except Exception as e:
            st.markdown(f'<div class="error-block">ERR · {e}</div>', unsafe_allow_html=True)
            st.stop()

    st.markdown(f"""
    <div class="page-header">
      <div class="page-title">{gp.upper()} {year}</div>
      <div class="page-meta">{session_label.upper()} · {d1} vs {d2}</div>
    </div>
    """, unsafe_allow_html=True)

    delta_end  = s["cumulative_delta_s"]
    delta_sign = "+" if delta_end > 0 else ""
    _lat_vals  = [v for v in [s["max_lat_g"][d1], s["max_lat_g"][d2]] if v is not None]
    _peak_lat  = f"{max(_lat_vals):.2f}" if _lat_vals else "—"

    st.markdown(f"""
    <div class="stat-strip">
      <div class="stat-cell"><div class="stat-label">Lap · {d1}</div><div class="stat-value stat-accent-1">{s['lap_times'][d1]}</div></div>
      <div class="stat-cell"><div class="stat-label">Lap · {d2}</div><div class="stat-value stat-accent-2">{s['lap_times'][d2]}</div></div>
      <div class="stat-cell"><div class="stat-label">Top speed</div><div class="stat-value">{max(s['top_speed'][d1], s['top_speed'][d2]):.0f}<span class="stat-unit">km/h</span></div></div>
      <div class="stat-cell"><div class="stat-label">Peak lat G</div><div class="stat-value">{_peak_lat}<span class="stat-unit">G</span></div></div>
      <div class="stat-cell"><div class="stat-label">End Δ</div><div class="stat-value stat-accent-delta">{delta_sign}{delta_end:.3f}<span class="stat-unit">s</span></div></div>
    </div>
    """, unsafe_allow_html=True)

    # Velocity + Delta
    st.markdown('<div class="section-label">Velocity &amp; time delta</div>', unsafe_allow_html=True)
    col_v, col_d = st.columns([3, 2])
    with col_v:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data["Distance"], y=data[f"Speed_smooth_{d1}"], name=d1, line=dict(color=C1, width=1.8)))
        fig.add_trace(go.Scatter(x=data["Distance"], y=data[f"Speed_smooth_{d2}"], name=d2, line=dict(color=C2, width=1.8)))
        fig.update_layout(**make_layout(yaxis={"title": "km/h"}, xaxis={"title": "distance (m)"}, height=280))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with col_d:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=data["Distance"], y=data["Delta"], fill="tozeroy", fillcolor="rgba(200,255,0,0.07)", line=dict(color=CD, width=1.5), name="Δ"))
        fig2.add_hline(y=0, line=dict(color="#2a2a2a", width=1))
        fig2.update_layout(**make_layout(yaxis={"title": "Δ s"}, xaxis={"title": "distance (m)"}, height=280))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # Sector table
    st.markdown('<div class="section-label">Mini-sector breakdown</div>', unsafe_allow_html=True)
    rows = "".join([f"""<tr>
          <td style="color:#555">{int(row['Sector']):02d}</td>
          <td>{row['Dist_start']:.0f}–{row['Dist_end']:.0f} m</td>
          <td><span class="stat-accent-1">{row[f'AvgSpeed_{d1}']:.1f}</span></td>
          <td><span class="stat-accent-2">{row[f'AvgSpeed_{d2}']:.1f}</span></td>
          <td>{row[f'PeakBrake_{d1}']:.2f}</td>
          <td>{row[f'PeakBrake_{d2}']:.2f}</td>
          <td class="{'gain' if row['Delta_gained'] >= 0 else 'loss'}">{'+' if row['Delta_gained'] >= 0 else ''}{row['Delta_gained']:.3f}s</td>
        </tr>""" for _, row in sectors.iterrows()])
    
    st.markdown(f"""
    <table class="sector-table">
      <thead><tr><th>#</th><th>Distance</th><th>Avg spd · {d1}</th><th>Avg spd · {d2}</th><th>Pk brk · {d1}</th><th>Pk brk · {d2}</th><th>Δ gained</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="status-bar">
      <span>{s['data_points']} pts · {n_sectors} sectors</span>
      <span>{d1}: {s['compounds'][d1]} · {d2}: {s['compounds'][d2]}</span>
      <span>FastF1 · MARS Engineering © 2026</span>
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="idle-wrap">
      <div class="idle-title">Welcome to F1 Telemetry</div>
      <div class="idle-sub">Formula 1 Battle Engine · Compare Driver Performance</div>
      <div style="margin-top: 40px; font-size: 12px; color: #555; letter-spacing: 0.08em; line-height: 1.8;">
        <div>Open the sidebar to select:</div>
        <div style="margin-top: 12px; color: #444;">Season · Circuit · Session · Drivers</div>
        <div style="margin-top: 20px; font-size: 11px; color: #444;">Then click ▶ RUN ANALYSIS</div>
      </div>
    </div>
    """, unsafe_allow_html=True)