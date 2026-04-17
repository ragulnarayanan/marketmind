"""
MarketMind — Streamlit entry point.
Handles auth gate, Qdrant collection init, and sidebar navigation.
"""
import os

import streamlit as st

st.set_page_config(
    page_title="MarketMind",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global theme CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset & Base ─────────────────────────────────────────────── */
*, *::before, *::after {
    box-sizing: border-box;
    text-transform: none !important;
}

.stApp, .main, [data-testid="stAppViewContainer"] {
    background: #000000 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Hide auto-generated Streamlit nav (prevents duplicate menu + tooltips) ─ */
[data-testid="stSidebarNav"] {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
}

/* ── Hide sidebar collapse/expand button (shows keyboard_double_arrow text) ─ */
[data-testid="collapsedControl"],
button[data-testid="baseButton-headerNoPadding"],
[data-testid="stSidebarCollapseButton"],
.st-emotion-cache-1egp75f,
section[data-testid="stSidebar"] > div:first-child button {
    display: none !important;
}
/* Hide any raw Material Icon text that leaks through */
span[class*="icon"]:not([data-testid]),
[data-testid="stPageLink"] span[class*="material"] {
    display: none !important;
}

/* ── st.page_link styling ─────────────────────────────────────────── */
[data-testid="stPageLink"] {
    padding: 0 !important;
    margin: 0 !important;
}
[data-testid="stPageLink"] a {
    display: block !important;
    padding: 9px 12px !important;
    border-radius: 6px !important;
    text-decoration: none !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #a1a1aa !important;
    transition: all 0.15s ease !important;
}
[data-testid="stPageLink"] a:hover {
    color: #ffffff !important;
    background: #111111 !important;
}
[data-testid="stPageLink"] a[aria-current="page"] {
    color: #76b900 !important;
    background: rgba(118,185,0,0.08) !important;
    border-left: 2px solid #76b900 !important;
    padding-left: 10px !important;
}
/* Hide the keyboard_double_arrow_right icon */
[data-testid="stPageLink"] a svg,
[data-testid="stPageLink"] [data-testid="stPageLinkIcon"],
[data-testid="stPageLink"] span[data-testid="stIconMaterial"] {
    display: none !important;
}

/* ── Sidebar ──────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #0a0a0a !important;
    border-right: 1px solid #1a1a1a !important;
}

/* ── Headings ─────────────────────────────────────────────────── */
h1 {
    font-family: 'Inter', sans-serif !important;
    font-size: 28px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    letter-spacing: -0.02em !important;
    text-transform: none !important;
}
h2 {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #76b900 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid rgba(118,185,0,0.2) !important;
    padding-bottom: 8px !important;
    margin-bottom: 16px !important;
}
h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    color: #ffffff !important;
    text-transform: none !important;
}
h4 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    color: #ffffff !important;
}
p, span, div, label, li {
    font-family: 'Inter', sans-serif !important;
    color: #a1a1aa;
}

/* ── Metric cards ─────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
    padding: 16px 20px !important;
    transition: border-color 0.2s ease, background 0.2s ease !important;
}
[data-testid="stMetric"]:hover {
    border-color: #76b900 !important;
    background: rgba(118,185,0,0.04) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    font-weight: 500 !important;
    color: #52525b !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stMetricValue"] {
    font-size: 24px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMetricDelta"] {
    font-size: 13px !important;
    font-weight: 500 !important;
}
[data-testid="stMetricDelta"][data-direction="up"]   { color: #76b900 !important; }
[data-testid="stMetricDelta"][data-direction="down"]  { color: #a1a1aa !important; }

/* ── Buttons ──────────────────────────────────────────────────── */
.stButton > button,
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-secondary"],
button[data-testid="stBaseButton-tertiary"],
[data-testid="stForm"] button,
.stButton button {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    background: #76b900 !important;
    color: #000000 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    transition: background 0.2s ease, transform 0.1s ease,
                box-shadow 0.2s ease !important;
    text-transform: none !important;
}
.stButton > button *,
button[data-testid="stBaseButton-primary"] *,
button[data-testid="stBaseButton-secondary"] *,
button[data-testid="stBaseButton-tertiary"] *,
button[data-testid="stFormSubmitButton"] *,
.stButton button *,
.stFormSubmitButton button * {
    color: #000000 !important;
}
.stButton > button:hover,
button[data-testid="stBaseButton-primary"]:hover,
button[data-testid="stBaseButton-secondary"]:hover,
button[data-testid="stBaseButton-tertiary"]:hover {
    background: #8fd400 !important;
    box-shadow: 0 0 16px rgba(118,185,0,0.3) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active,
button[data-testid="stBaseButton-primary"]:active,
button[data-testid="stBaseButton-secondary"]:active {
    transform: translateY(0) !important;
    background: #5a8c00 !important;
}

/* ── Text inputs ──────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
textarea {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    background: #0a0a0a !important;
    color: #ffffff !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 8px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
textarea:focus {
    border-color: #76b900 !important;
    box-shadow: 0 0 0 3px rgba(118,185,0,0.12) !important;
    outline: none !important;
}

/* ── Selectbox ────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 8px !important;
    color: #ffffff !important;
}

/* ── DataFrames / Tables ──────────────────────────────────────── */
[data-testid="stDataFrame"], .stDataFrame {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
}
[data-testid="stDataFrame"] th {
    background: #111111 !important;
    color: #52525b !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border-bottom: 1px solid #1a1a1a !important;
}
[data-testid="stDataFrame"] td {
    color: #ffffff !important;
    font-size: 14px !important;
    border-bottom: 1px solid #0f0f0f !important;
}

/* ── Expanders ────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"]:hover {
    border-color: #76b900 !important;
}
[data-testid="stExpander"] summary {
    color: #ffffff !important;
    font-weight: 500 !important;
}

/* ── Dividers ─────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid #76b900 !important;
    opacity: 0.3 !important;
    margin: 24px 0 !important;
}

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #000000; }
::-webkit-scrollbar-thumb {
    background: #76b900;
    border-radius: 2px;
}
::-webkit-scrollbar-thumb:hover { background: #5a8c00; }

/* ── Status / spinner ─────────────────────────────────────────── */
[data-testid="stStatusWidget"] {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
}

/* ── Alerts / info boxes ──────────────────────────────────────── */
[data-testid="stAlert"] {
    background: #0a0a0a !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Caption / small text ─────────────────────────────────────── */
[data-testid="stCaptionContainer"] {
    color: #52525b !important;
    font-size: 12px !important;
}

/* ── Tabs ─────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    background: #0a0a0a !important;
    border-bottom: 1px solid #1a1a1a !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [role="tab"] {
    color: #52525b !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.15s ease !important;
    text-transform: none !important;
}
[data-testid="stTabs"] [role="tab"]:hover {
    color: #ffffff !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #76b900 !important;
    border-bottom: 2px solid #76b900 !important;
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

# ── Qdrant collection bootstrap (once per session) ────────────────────────────
if not st.session_state.get("_qdrant_init"):
    try:
        from data.qdrant_client import init_collections
        init_collections()
        st.session_state["_qdrant_init"] = True
    except Exception as e:
        st.warning(f"Qdrant unavailable — vector search disabled. ({e})")
        st.session_state["_qdrant_init"] = False

# ── Auth gate ──────────────────────────────────────────────────────────────────
TEST_UID = os.getenv("TEST_UID")

if TEST_UID and not st.session_state.get("uid"):
    st.session_state["uid"]          = TEST_UID
    st.session_state["display_name"] = "Dev User"
    st.session_state["email"]        = "dev@example.com"
    try:
        from data.firestore_client import get_or_create_user
        get_or_create_user(TEST_UID, "dev@example.com", "Dev User")
    except Exception:
        pass

if not st.session_state.get("uid"):
    st.title("MarketMind")
    st.markdown("### AI-powered stock research and daily portfolio brief")
    st.divider()

    st.markdown("<h2 style='color:#76b900;border-bottom:1px solid rgba(118,185,0,0.2);padding-bottom:8px;font-family:Inter,sans-serif;letter-spacing:0.06em;text-transform:uppercase;font-size:14px'>Sign In</h2>", unsafe_allow_html=True)

    st.markdown(
        "<p style='color:#6b7280;font-size:13px;margin-bottom:16px'>"
        "Returning user? Sign in with the same User ID and email you registered with. "
        "New here? Fill in all three fields to create your account."
        "</p>",
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        user_id      = st.text_input("User ID", placeholder="your-unique-id")
        email        = st.text_input("Email", placeholder="you@example.com")
        display_name = st.text_input("Display Name", placeholder="Jane Smith (only needed for new accounts)")
        submitted    = st.form_submit_button("Sign In", type="primary")

        if submitted:
            if not user_id or not email:
                st.error("User ID and email are required.")
            else:
                try:
                    from data.firestore_client import get_user, get_or_create_user
                    existing = get_user(user_id)
                    if existing:
                        # Returning user — load saved name, ignore entered display name
                        saved_name = existing.get("display_name", "User")
                    else:
                        # New user — use entered display name
                        saved_name = display_name.strip() or "User"
                        get_or_create_user(user_id, email, saved_name)
                    st.session_state["uid"]          = user_id
                    st.session_state["display_name"] = saved_name
                    st.session_state["email"]        = email
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign-in failed: {e}")
    st.stop()

# ── Main page (authenticated) ──────────────────────────────────────────────────
uid          = st.session_state["uid"]
display_name = st.session_state.get("display_name", "User")

from utils.nav import render_nav
render_nav()

st.markdown("""
<style>
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] span,
[data-testid="stAppViewContainer"] div,
[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,
[data-testid="stAppViewContainer"] h4 {
    color: #ffffff !important;
}
/* keep button text black */
[data-testid="stAppViewContainer"] button,
[data-testid="stAppViewContainer"] button *,
[data-testid="stAppViewContainer"] button p,
[data-testid="stAppViewContainer"] button span,
[data-testid="stAppViewContainer"] button div {
    color: #000000 !important;
}
</style>
""", unsafe_allow_html=True)

top_left, top_right = st.columns([6, 1])
with top_left:
    st.title("MarketMind")
    st.markdown("<p style='color:#ffffff;font-size:15px'>Welcome back, <b>{}</b>.</p>".format(display_name), unsafe_allow_html=True)
with top_right:
    st.markdown("<div style='padding-top:20px'></div>", unsafe_allow_html=True)
    if st.button("Sign Out", key="home_sign_out"):
        for key in ["uid", "display_name", "email"]:
            st.session_state.pop(key, None)
        st.rerun()

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.markdown("### Daily Brief")
    st.markdown("<p style='color:#ffffff'>Get your personalized portfolio P&L, news summaries, macro alerts, and buy/wait signals.</p>", unsafe_allow_html=True)
    if st.button("Open Daily Brief", key="home_brief", type="primary"):
        st.switch_page("pages/01_daily_brief.py")

with col2:
    st.markdown("### Stock Research")
    st.markdown("<p style='color:#ffffff'>Enter any ticker for a five-agent deep dive: news, SEC filings, financials, and a Buy/Hold/Sell verdict.</p>", unsafe_allow_html=True)
    if st.button("Open Research", key="home_research", type="primary"):
        st.switch_page("pages/02_stock_research.py")

# ── Animated market chart footer ──────────────────────────────────────────────
import streamlit.components.v1 as _components
_components.html("""
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: transparent; overflow: hidden; }
  #wrap {
    background: #0a0a0a;
    border: 1px solid #1a1a1a;
    border-radius: 12px;
    padding: 14px 18px 10px;
    position: relative;
  }
  #topRow {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }
  #chartTitle {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: #52525b;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  #priceLabel {
    font-family: 'Inter', monospace;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }
  canvas { display: block; width: 100%; height: 160px; }
</style>

<div id="wrap">
  <div id="topRow">
    <span id="chartTitle">MarketMind · Simulated Live Feed</span>
    <span id="priceLabel">—</span>
  </div>
  <canvas id="chart"></canvas>
</div>

<script>
  const canvas    = document.getElementById('chart');
  const ctx       = canvas.getContext('2d');
  const priceEl   = document.getElementById('priceLabel');

  function resize() {
    canvas.width  = canvas.offsetWidth  * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  }
  resize();
  window.addEventListener('resize', () => { resize(); });

  const POINTS = 100;
  const SPEED  = 0.25;   // pixels per frame — slow scroll
  const MEAN   = 150;    // mean-revert target
  const VOL    = 2.2;    // volatility per new bar

  let prices = [];
  let offset = 0;

  // Seed with a mean-reverting walk
  let p = MEAN;
  for (let i = 0; i < POINTS + 2; i++) {
    p += (MEAN - p) * 0.03 + (Math.random() - 0.5) * VOL * 2;
    p  = Math.max(50, Math.min(250, p));
    prices.push(p);
  }

  function addBar() {
    let last = prices[prices.length - 1];
    last += (MEAN - last) * 0.03 + (Math.random() - 0.5) * VOL * 2;
    last  = Math.max(50, Math.min(250, last));
    prices.push(last);
    if (prices.length > POINTS + 20) prices.shift();
  }

  function smoothPath(pts, toX, toY) {
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(pts[0]));
    for (let i = 0; i < pts.length - 1; i++) {
      const cx = (toX(i) + toX(i + 1)) / 2;
      ctx.bezierCurveTo(cx, toY(pts[i]), cx, toY(pts[i + 1]), toX(i + 1), toY(pts[i + 1]));
    }
  }

  function draw() {
    const W = canvas.offsetWidth;
    const H = canvas.offsetHeight;
    ctx.clearRect(0, 0, W, H);

    offset += SPEED;
    if (offset >= 1) {
      offset -= 1;
      addBar();
    }

    const visible = prices.slice(-(POINTS + 1));
    const vals    = visible;
    const minV    = Math.min(...vals) - 8;
    const maxV    = Math.max(...vals) + 8;
    const range   = maxV - minV || 1;

    const PAD_L = 8, PAD_R = 52, PAD_T = 8, PAD_B = 24;
    const cW    = W - PAD_L - PAD_R;
    const cH    = H - PAD_T - PAD_B;

    const toX = i  => PAD_L + ((i - offset) / (POINTS - 1)) * cW;
    const toY = v  => PAD_T + cH - ((v - minV) / range) * cH;

    // ── Grid lines ──────────────────────────────────────────────
    const gridLines = 4;
    ctx.setLineDash([3, 5]);
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth   = 1;
    for (let g = 0; g <= gridLines; g++) {
      const gy = PAD_T + (g / gridLines) * cH;
      ctx.beginPath();
      ctx.moveTo(PAD_L, gy);
      ctx.lineTo(W - PAD_R, gy);
      ctx.stroke();
      // Y-axis label
      const price = maxV - (g / gridLines) * range;
      ctx.font      = '10px monospace';
      ctx.fillStyle = '#3f3f46';
      ctx.textAlign = 'left';
      ctx.fillText(price.toFixed(0), W - PAD_R + 6, gy + 4);
    }
    ctx.setLineDash([]);

    // Determine overall direction (first vs last visible point)
    const firstP = visible[0];
    const lastP  = visible[visible.length - 1];
    const rising = lastP >= firstP;
    const lineColor = rising ? '#76b900' : '#e53e3e';
    const fillColor = rising ? 'rgba(118,185,0,' : 'rgba(229,62,62,';

    // ── Gradient fill under curve ────────────────────────────────
    const grad = ctx.createLinearGradient(0, PAD_T, 0, PAD_T + cH);
    grad.addColorStop(0, fillColor + '0.18)');
    grad.addColorStop(1, fillColor + '0.0)');

    smoothPath(visible, toX, toY);
    ctx.lineTo(toX(visible.length - 1), PAD_T + cH);
    ctx.lineTo(toX(0), PAD_T + cH);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // ── Price line ───────────────────────────────────────────────
    smoothPath(visible, toX, toY);
    ctx.strokeStyle = lineColor;
    ctx.lineWidth   = 2;
    ctx.lineJoin    = 'round';
    ctx.stroke();

    // ── Glowing live dot ─────────────────────────────────────────
    const lx = toX(visible.length - 1);
    const ly = toY(lastP);
    ctx.shadowColor = lineColor;
    ctx.shadowBlur  = 12;
    ctx.beginPath();
    ctx.arc(lx, ly, 4, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.fill();
    ctx.shadowBlur  = 0;

    // ── Horizontal dashed line at live price ─────────────────────
    ctx.setLineDash([4, 6]);
    ctx.strokeStyle = lineColor + '66';
    ctx.lineWidth   = 1;
    ctx.beginPath();
    ctx.moveTo(lx, ly);
    ctx.lineTo(W - PAD_R, ly);
    ctx.stroke();
    ctx.setLineDash([]);

    // ── Live price tag on right axis ─────────────────────────────
    const tagH = 16, tagW = 44;
    const tagX = W - PAD_R + 2;
    const tagY = ly - tagH / 2;
    ctx.fillStyle   = lineColor;
    ctx.beginPath();
    ctx.roundRect(tagX, tagY, tagW, tagH, 3);
    ctx.fill();
    ctx.font      = 'bold 10px monospace';
    ctx.fillStyle = '#000000';
    ctx.textAlign = 'center';
    ctx.fillText(lastP.toFixed(2), tagX + tagW / 2, tagY + 11);

    // ── Update price label above chart ───────────────────────────
    const chg    = lastP - firstP;
    const chgPct = ((chg / firstP) * 100).toFixed(2);
    priceEl.textContent = lastP.toFixed(2) + '  ' + (chg >= 0 ? '+' : '') + chgPct + '%';
    priceEl.style.color = rising ? '#76b900' : '#e53e3e';

    requestAnimationFrame(draw);
  }

  draw();
</script>
""", height=240)
