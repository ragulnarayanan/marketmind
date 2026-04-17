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
    st.markdown(
        "<h1 style='font-family:Inter,sans-serif;font-size:52px;font-weight:700;"
        "letter-spacing:-0.03em;color:#ffffff;margin:0 0 4px 0;line-height:1.1'>"
        "MarketM<span style='position:relative;display:inline-block'>&#x131;"
        "<span style='position:absolute;left:50%;top:0.24em;transform:translateX(-50%);"
        "width:0.17em;height:0.17em;background:#76b900;border-radius:50%;display:block'>"
        "</span></span>nd</h1>",
        unsafe_allow_html=True,
    )
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
[data-testid="stAppViewContainer"] h1 {
    font-size: 52px !important;
    letter-spacing: -0.03em !important;
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
    import streamlit.components.v1 as _cv1
    _cv1.html("""<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@700&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{background:transparent;overflow:visible}
  #stage{position:relative;padding-top:46px;perspective:600px}
  #ghost{
    font-family:'Inter',sans-serif;font-size:52px;font-weight:700;
    letter-spacing:-0.03em;line-height:1;white-space:nowrap;
    opacity:0;pointer-events:none;user-select:none
  }
  .al{
    font-family:'Inter',sans-serif;font-size:52px;font-weight:700;
    letter-spacing:-0.03em;line-height:1;color:#fff;
    position:absolute;white-space:nowrap;opacity:0
  }
  #dot{
    position:absolute;background:#76b900;border-radius:50%;
    pointer-events:none;opacity:0;
    box-shadow:0 0 8px #76b900,0 0 18px rgba(118,185,0,.4)
  }
</style>
</head>
<body>
<div id="stage">
  <div id="ghost"><span id="g0">M</span><span id="g1">a</span><span id="g2">r</span><span id="g3">k</span><span id="g4">e</span><span id="g5">t</span><span id="g6">M</span><span id="g7">&#x131;</span><span id="g8">n</span><span id="g9">d</span></div>
  <span id="l0" class="al">M</span><span id="l1" class="al">a</span><span id="l2" class="al">r</span><span id="l3" class="al">k</span><span id="l4" class="al">e</span><span id="l5" class="al">t</span><span id="l6" class="al">M</span><span id="l7" class="al">&#x131;</span><span id="l8" class="al">n</span><span id="l9" class="al">d</span>
  <div id="dot"></div>
</div>
<script>
(function(){
setTimeout(function(){
  const stage = document.getElementById('stage');
  const sr    = stage.getBoundingClientRect();
  const fp    = Array.from({length:10},(_,i)=>{
    const r=document.getElementById('g'+i).getBoundingClientRect();
    return {x:r.left-sr.left,y:r.top-sr.top,w:r.width,h:r.height};
  });
  const ls  = Array.from({length:10},(_,i)=>document.getElementById('l'+i));
  const dot = document.getElementById('dot');

  ls.forEach((el,i)=>{ el.style.left=fp[i].x+'px'; el.style.top=fp[i].y+'px'; });

  const wCx = fp[0].x + (fp[9].x+fp[9].w - fp[0].x)/2 - fp[0].w/2; // center x for M start

  // ── Timing constants (ms) ──────────────────────────
  const D_SPIN   = 1300;  // M flips in sideways
  const D_SPLIT  = 700;   // M splits into two
  const D_UNFOLD = 1000;  // letters unfold
  const D_HOP    = 950;   // each dot hop
  const D_SETTLE = 700;   // dot settles on i
  const D_WAIT   = 3500;  // wait before restart
  const D_FADE   = 700;   // fade everything out
  const D_PAUSE  = 1800;  // blank pause before next loop

  const PHASES = [
    {name:'spin',   dur:D_SPIN},
    {name:'split',  dur:D_SPLIT},
    {name:'unfold', dur:D_UNFOLD},
    {name:'hop1',   dur:D_HOP},    // dot: M1 → k
    {name:'hop2',   dur:D_HOP},    // dot: k  → M2
    {name:'hop3',   dur:D_HOP},    // dot: M2 → i
    {name:'settle', dur:D_SETTLE},
    {name:'wait',   dur:D_WAIT},
    {name:'fade',   dur:D_FADE},
    {name:'pause',  dur:D_PAUSE},
  ];

  function easeOut(t){return 1-Math.pow(1-t,3)}
  function easeIO(t){return t<.5?2*t*t:-1+(4-2*t)*t}

  function dp(idx){  // dot anchor position for letter idx
    return {x:fp[idx].x+fp[idx].w*.5, y:fp[idx].y+fp[idx].h*.07, sz:fp[idx].h*.13};
  }
  function setDot(x,y,sz,op){
    dot.style.width=sz+'px'; dot.style.height=sz+'px';
    dot.style.left=(x-sz/2)+'px'; dot.style.top=y+'px'; dot.style.opacity=op;
  }

  function reset(){
    ls.forEach(el=>{ el.style.opacity='0'; el.style.transform=''; });
    ls.forEach((el,i)=>{ el.style.left=fp[i].x+'px'; });
    ls[0].style.left=wCx+'px';
    dot.style.opacity='0';
  }

  let pi=0, ps=null;

  function frame(ts){
    if(!ps) ps=ts;
    const el = ts-ps;
    const ph = PHASES[pi];
    const t  = Math.min(el/ph.dur, 1);
    const et = easeOut(t);
    const ARC = 36;

    switch(ph.name){

      case 'spin':
        // M flips in sideways: full 360° rotateY while scaling 0→1
        ls[0].style.left    = wCx+'px';
        ls[0].style.opacity = Math.min(t*3,1).toFixed(3);
        ls[0].style.transform = `perspective(300px) rotateY(${(1-et)*360}deg) scale(${et})`;
        ls[6].style.opacity='0';
        break;

      case 'split':
        // M1 slides to final left pos; M2 fades+scales in from center
        ls[0].style.transform='';
        ls[0].style.left=(wCx+(fp[0].x-wCx)*et)+'px';
        ls[0].style.opacity='1';
        ls[6].style.left=(wCx+(fp[6].x-wCx)*et)+'px';
        ls[6].style.opacity=Math.min(t*2,1).toFixed(3);
        ls[6].style.transform=`scale(${.4+et*.6})`;
        break;

      case 'unfold':
        ls[0].style.left=fp[0].x+'px'; ls[0].style.transform='';
        ls[6].style.left=fp[6].x+'px'; ls[6].style.transform=''; ls[6].style.opacity='1';
        [1,2,3,4,5].forEach((idx,ord)=>{
          const lt=Math.max(0,Math.min((el-ord*90)/220,1)), e2=easeOut(lt);
          ls[idx].style.opacity=e2.toFixed(3);
          ls[idx].style.transform=`scaleX(${e2})`;
          ls[idx].style.transformOrigin='left center';
        });
        [7,8,9].forEach((idx,ord)=>{
          const lt=Math.max(0,Math.min((el-ord*90)/220,1)), e2=easeOut(lt);
          ls[idx].style.opacity=e2.toFixed(3);
          ls[idx].style.transform=`scaleX(${e2})`;
          ls[idx].style.transformOrigin='left center';
        });
        break;

      case 'hop1':{ // M1(0) → k(3)
        ls.forEach((e2,i)=>{ e2.style.opacity='1'; e2.style.transform=''; e2.style.left=fp[i].x+'px'; });
        const A=dp(0),B=dp(3),eit=easeIO(t);
        setDot(A.x+(B.x-A.x)*eit, A.y+(B.y-A.y)*eit-ARC*Math.sin(eit*Math.PI), A.sz+(B.sz-A.sz)*eit, '1');
        break;}

      case 'hop2':{ // k(3) → M2(6)
        const A=dp(3),B=dp(6),eit=easeIO(t);
        setDot(A.x+(B.x-A.x)*eit, A.y+(B.y-A.y)*eit-ARC*Math.sin(eit*Math.PI), A.sz+(B.sz-A.sz)*eit, '1');
        break;}

      case 'hop3':{ // M2(6) → i(7)
        const A=dp(6),B=dp(7),eit=easeIO(t);
        setDot(A.x+(B.x-A.x)*eit, A.y+(B.y-A.y)*eit-ARC*Math.sin(eit*Math.PI), A.sz+(B.sz-A.sz)*eit, '1');
        break;}

      case 'settle':{
        const p=dp(7);
        const bob=Math.abs(Math.sin(t*Math.PI*2.5))*7*Math.max(0,1-t*2.5);
        setDot(p.x, p.y-bob, p.sz, '1');
        break;}

      case 'wait':
        setDot(dp(7).x, dp(7).y, dp(7).sz, '1');
        break;

      case 'fade':{
        const op=(1-et).toFixed(3);
        ls.forEach(el=>{ el.style.opacity=op; });
        dot.style.opacity=op;
        break;}

      case 'pause':
        ls.forEach(el=>{ el.style.opacity='0'; }); dot.style.opacity='0';
        break;
    }

    if(t>=1){
      pi=(pi+1)%PHASES.length;
      ps=ts;
      if(pi===0) reset();
    }
    requestAnimationFrame(frame);
  }

  reset();
  requestAnimationFrame(frame);
}, 450);
})();
</script>
</body>
</html>
""", height=112)
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
  html, body { background: transparent; overflow: hidden; width: 100%; height: 100%; }
  canvas { display: block; width: 100%; height: 100%; }
</style>
<canvas id="chart"></canvas>
<script>
  const canvas = document.getElementById('chart');
  const ctx    = canvas.getContext('2d');

  function resize() {
    canvas.width  = canvas.offsetWidth  * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  }
  resize();
  window.addEventListener('resize', resize);

  const POINTS = 120;
  const SPEED  = 0.03;
  const MEAN   = 150;
  const VOL    = 1.8;

  let prices = [];
  let offset = 0;

  let p = MEAN;
  for (let i = 0; i < POINTS + 5; i++) {
    p += (MEAN - p) * 0.03 + (Math.random() - 0.5) * VOL * 2;
    p  = Math.max(60, Math.min(240, p));
    prices.push(p);
  }

  function addBar() {
    let last = prices[prices.length - 1];
    last += (MEAN - last) * 0.03 + (Math.random() - 0.5) * VOL * 2;
    last  = Math.max(60, Math.min(240, last));
    prices.push(last);
    if (prices.length > POINTS + 20) prices.shift();
  }

  function smoothPath(pts, toX, toY) {
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(pts[0]));
    for (let i = 0; i < pts.length - 1; i++) {
      const cx = (toX(i) + toX(i + 1)) / 2;
      ctx.bezierCurveTo(cx, toY(pts[i]), cx, toY(pts[i+1]), toX(i+1), toY(pts[i+1]));
    }
  }

  function draw() {
    const W = canvas.offsetWidth;
    const H = canvas.offsetHeight;
    ctx.clearRect(0, 0, W, H);

    offset += SPEED;
    if (offset >= 1) { offset -= 1; addBar(); }

    const visible = prices.slice(-(POINTS + 1));
    const minV    = Math.min(...visible) - 10;
    const maxV    = Math.max(...visible) + 10;
    const range   = maxV - minV || 1;

    const PAD_T = 10, PAD_B = 10;
    const cH    = H - PAD_T - PAD_B;

    const toX = i => ((i - offset) / (POINTS - 1)) * W;
    const toY = v => PAD_T + cH - ((v - minV) / range) * cH;

    const firstP = visible[0];
    const lastP  = visible[visible.length - 1];
    const rising = lastP >= firstP;
    const lineColor  = rising ? '#76b900' : '#e53e3e';
    const fillColor  = rising ? 'rgba(118,185,0,' : 'rgba(229,62,62,';

    // Gradient fill
    const grad = ctx.createLinearGradient(0, PAD_T, 0, PAD_T + cH);
    grad.addColorStop(0, fillColor + '0.15)');
    grad.addColorStop(1, fillColor + '0.0)');
    smoothPath(visible, toX, toY);
    ctx.lineTo(toX(visible.length - 1), H);
    ctx.lineTo(toX(0), H);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    smoothPath(visible, toX, toY);
    ctx.strokeStyle = lineColor;
    ctx.lineWidth   = 2;
    ctx.lineJoin    = 'round';
    ctx.stroke();

    // Glowing tip dot
    const lx = toX(visible.length - 1);
    const ly = toY(lastP);
    ctx.shadowColor = lineColor;
    ctx.shadowBlur  = 14;
    ctx.beginPath();
    ctx.arc(lx, ly, 4, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.fill();
    ctx.shadowBlur = 0;

    requestAnimationFrame(draw);
  }

  draw();
</script>
""", height=320)
