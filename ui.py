"""
ui.py
=====
Premium design system for the RoadSense AI Streamlit app.

DESIGN LANGUAGE: this is a faithful translation of the "RootSense AI" web
project's aesthetic — a dark, neon "mission-control / observability cockpit"
look:

  * Near-black background with fixed radial neon glows (violet + cyan).
  * Neon accent palette: violet / cyan / pink / lime.
  * Glass cards with a soft corner glow-blob; hover lifts the border to primary.
  * Uppercase, letter-spaced micro-labels + display-font numerals.
  * Gradient text headings (violet → cyan → pink).
  * Subtle grid pattern, shimmer + pulse-glow animations, ~14px radii.
  * A muted light theme + the headline dark theme (toggle persisted to disk).

This module is PURE PRESENTATION — no business logic, no backend, no data.
The public API (inject_theme / hero / stat_card / …) is unchanged, so the rest
of the app keeps working exactly as before; only the visuals change.
"""

import json
from pathlib import Path

import streamlit as st

import config

# ---------------------------------------------------------------------------
# Brand constants (hex approximations of RootSense's neon HSL tokens).
# Used by the Python HTML helpers; the stylesheet itself uses CSS variables.
# ---------------------------------------------------------------------------
PRIMARY = "#8B5CF6"        # violet (primary)
NEON_VIOLET = "#A78BFA"
NEON_CYAN = "#34D3EC"
NEON_PINK = "#F871CE"
NEON_LIME = "#3BE38B"
SECONDARY = NEON_VIOLET
ACCENT = NEON_CYAN

SUCCESS = "#22C55E"
WARNING = "#F59E0B"
DANGER = "#EF4444"

# Per-hazard accent colours (used by stat cards / badges).
HAZARD_COLORS = {
    "pothole": DANGER,
    "crack": WARNING,
    "speed_breaker": NEON_VIOLET,
}

# Theme preference is persisted here so it survives app restarts.
_SETTINGS_PATH = config.DATABASE_DIR / "app_settings.json"


# ===========================================================================
# Theme persistence
# ===========================================================================
def load_theme() -> str:
    """Return the saved theme ('dark' or 'light'), defaulting to dark."""
    try:
        data = json.loads(Path(_SETTINGS_PATH).read_text(encoding="utf-8"))
        return "light" if data.get("theme") == "light" else "dark"
    except Exception:
        return "dark"


def save_theme(theme: str) -> None:
    """Persist the chosen theme to disk (best-effort, never raises)."""
    try:
        Path(_SETTINGS_PATH).write_text(
            json.dumps({"theme": theme}), encoding="utf-8"
        )
    except Exception:
        pass


def init_theme_state() -> None:
    """Load the persisted theme into session_state on first run."""
    if "theme" not in st.session_state:
        st.session_state.theme = load_theme()


def toggle_theme() -> None:
    """Flip light <-> dark, persist it, and rerun."""
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
    save_theme(st.session_state.theme)
    st.rerun()


def is_dark() -> bool:
    """Convenience accessor for the current theme."""
    return st.session_state.get("theme", "dark") == "dark"


# ===========================================================================
# Palette per theme (HSL triplets, exactly like RootSense's design tokens).
# Stored as raw "H S% L%" strings so CSS can apply alpha: hsl(var(--x) / .3)
# ===========================================================================
def _palette(dark: bool) -> dict:
    """Return the CSS-variable HSL triplets for the requested theme."""
    if dark:
        return {
            "bg": "240 14% 4%",
            "card": "240 12% 7%",
            "alt": "240 6% 12%",
            "border": "240 6% 16%",
            "text": "240 6% 96%",
            "muted": "240 5% 62%",
            "primary": "262 83% 68%",
        }
    return {
        "bg": "240 20% 99%",
        "card": "0 0% 100%",
        "alt": "240 6% 96%",
        "border": "240 6% 90%",
        "text": "240 10% 6%",
        "muted": "240 4% 46%",
        "primary": "262 83% 58%",
    }


# Neon accents — shared across themes (they read well on both).
_NEON = {
    "violet": "262 90% 72%",
    "cyan": "188 94% 60%",
    "pink": "322 92% 68%",
    "lime": "142 76% 58%",
}


# ===========================================================================
# The global stylesheet
# ===========================================================================
def inject_theme() -> None:
    """
    Inject the full RootSense-style stylesheet for the current theme.

    Call once near the top of every page render. Styles native Streamlit
    widgets (buttons, inputs, metrics, sidebar, tabs, dataframes) plus the
    custom component classes.
    """
    init_theme_state()
    dark = is_dark()
    p = _palette(dark)
    n = _NEON
    glow_op = "0.16" if dark else "0.10"

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

        :root {{
            --bg:{p['bg']}; --card:{p['card']}; --alt:{p['alt']};
            --border:{p['border']}; --text:{p['text']}; --muted:{p['muted']};
            --primary:{p['primary']};
            --violet:{n['violet']}; --cyan:{n['cyan']};
            --pink:{n['pink']}; --lime:{n['lime']};
            --radius: 14px;
            --grad-text: linear-gradient(135deg, hsl(var(--violet)), hsl(var(--cyan)) 55%, hsl(var(--pink)));
            --grad-brand: linear-gradient(135deg, hsl(262 83% 62%), hsl(188 90% 52%));
        }}

        /* ---- App shell: near-black + fixed radial neon glows + grid ---- */
        .stApp {{
            background: hsl(var(--bg));
            color: hsl(var(--text));
            font-family: 'Inter', system-ui, sans-serif;
        }}
        .stApp::before {{
            content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
            background:
              radial-gradient(1200px 600px at 82% -18%, hsl(var(--violet) / {glow_op}), transparent 60%),
              radial-gradient(900px 520px at -12% 8%, hsl(var(--cyan) / {glow_op}), transparent 60%);
        }}
        .stApp::after {{
            content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
            background-image:
              linear-gradient(to right, hsl(var(--border) / .5) 1px, transparent 1px),
              linear-gradient(to bottom, hsl(var(--border) / .5) 1px, transparent 1px);
            background-size: 34px 34px;
            -webkit-mask-image: radial-gradient(ellipse at 50% 0%, black 8%, transparent 60%);
            mask-image: radial-gradient(ellipse at 50% 0%, black 8%, transparent 60%);
            opacity: .5;
        }}
        .block-container {{ position:relative; z-index:1; padding-top:1.4rem;
            max-width:1500px; padding-left:2.2rem; padding-right:2.2rem; }}

        /* Hide Streamlit chrome for an app-like feel */
        #MainMenu, footer, [data-testid="stToolbar"] {{ visibility:hidden; height:0; }}
        [data-testid="stHeader"] {{ background:transparent; }}

        /* ---- Typography ---- */
        h1,h2,h3 {{ font-family:'Space Grotesk','Inter',sans-serif !important;
            letter-spacing:-.5px; color:hsl(var(--text)); }}
        p,span,label,div,li {{ color:hsl(var(--text)); }}
        .stCaption, [data-testid="stCaptionContainer"] {{ color:hsl(var(--muted)) !important; }}
        code {{ font-family:'JetBrains Mono',monospace !important;
            background:hsl(var(--alt)) !important; color:hsl(var(--cyan)) !important;
            border-radius:6px; padding:1px 6px; }}

        /* ---- Buttons ---- */
        .stButton > button, .stDownloadButton > button {{
            border-radius:var(--radius) !important;
            border:1px solid hsl(var(--border)) !important;
            background:hsl(var(--alt) / .7) !important;
            color:hsl(var(--text)) !important;
            font-weight:600 !important; padding:.55rem 1rem !important;
            backdrop-filter: blur(8px);
            transition: transform .12s ease, box-shadow .2s ease, border-color .2s ease !important;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            transform:translateY(-2px); border-color:hsl(var(--primary) / .5) !important;
            box-shadow:0 0 0 1px hsl(var(--primary) / .3), 0 12px 30px -12px hsl(var(--violet) / .5) !important;
        }}
        .stButton > button:active {{ transform:translateY(0) scale(.985); }}
        .stButton > button[kind="primary"],
        .stButton > button[kind="primaryFormSubmit"],
        .stForm [data-testid="stFormSubmitButton"] button {{
            background:var(--grad-brand) !important; color:#fff !important;
            border:none !important;
            box-shadow:0 0 24px -6px hsl(var(--violet) / .8), 0 8px 22px -8px hsl(var(--cyan) / .6) !important;
        }}
        .stButton > button[kind="primary"]:hover {{ filter:brightness(1.08); }}

        /* ---- Text inputs ---- */
        .stTextInput input, .stNumberInput input {{
            background:hsl(var(--alt) / .6) !important; color:hsl(var(--text)) !important;
            border-radius:var(--radius) !important;
            border:1px solid hsl(var(--border)) !important; padding:.7rem .9rem !important;
        }}
        .stTextInput input:focus {{ border-color:hsl(var(--primary)) !important;
            box-shadow:0 0 0 3px hsl(var(--primary) / .28) !important; }}
        [data-baseweb="select"] > div {{
            background:hsl(var(--alt) / .6) !important; border-radius:var(--radius) !important;
            border:1px solid hsl(var(--border)) !important; }}

        /* ---- Metrics -> cockpit tiles ---- */
        [data-testid="stMetric"] {{
            position:relative; overflow:hidden;
            background:hsl(var(--card) / .6); border:1px solid hsl(var(--border));
            border-radius:18px; padding:16px 18px;
            box-shadow:0 0 0 1px hsl(var(--border) / .6), 0 20px 60px -30px rgba(0,0,0,.6);
            backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
            transition:border-color .2s ease, transform .15s ease;
        }}
        [data-testid="stMetric"]::after {{
            content:""; position:absolute; top:-40px; right:-40px; width:120px; height:120px;
            border-radius:50%; filter:blur(38px); opacity:.5;
            background:radial-gradient(closest-side, hsl(var(--violet) / .5), transparent);
        }}
        [data-testid="stMetric"]:hover {{ transform:translateY(-3px);
            border-color:hsl(var(--primary) / .4); }}
        [data-testid="stMetricLabel"] p {{ color:hsl(var(--muted)) !important;
            text-transform:uppercase; letter-spacing:1.5px; font-size:.7rem !important;
            font-weight:600; font-family:'JetBrains Mono',monospace !important; }}
        [data-testid="stMetricValue"] {{ font-family:'Space Grotesk',sans-serif !important;
            font-weight:600; letter-spacing:-.5px; }}

        /* ---- Sidebar ---- */
        [data-testid="stSidebar"] {{
            background:hsl(var(--card)); border-right:1px solid hsl(var(--border));
            backdrop-filter:blur(12px);
        }}
        [data-testid="stSidebar"] .stButton > button {{ width:100%; }}

        /* ---- Tabs ---- */
        .stTabs [data-baseweb="tab"] {{ background:hsl(var(--alt) / .6);
            border-radius:12px; padding:6px 14px; }}
        .stTabs [aria-selected="true"] {{ background:var(--grad-brand) !important; color:#fff !important; }}

        /* ---- Dataframe / alerts ---- */
        [data-testid="stDataFrame"] {{ border-radius:16px; overflow:hidden;
            border:1px solid hsl(var(--border)); }}
        [data-testid="stAlert"] {{ border-radius:14px; border:1px solid hsl(var(--border));
            background:hsl(var(--alt) / .5); backdrop-filter:blur(8px); }}

        /* ==================== Custom components ==================== */
        .rs-hero {{
            position:relative; overflow:hidden;
            border-radius:24px; padding:44px 34px;
            background:
              radial-gradient(700px 300px at 88% -30%, hsl(var(--pink) / .18), transparent 60%),
              radial-gradient(700px 300px at 0% 120%, hsl(var(--cyan) / .16), transparent 60%),
              hsl(var(--card) / .7);
            border:1px solid hsl(var(--border));
            box-shadow:0 0 0 1px hsl(var(--violet) / .25), 0 30px 80px -40px hsl(var(--violet) / .7);
            backdrop-filter:blur(18px);
            animation: fadeIn .6s ease both;
        }}
        .rs-hero::before {{  /* grid overlay */
            content:""; position:absolute; inset:0; opacity:.4;
            background-image:
              linear-gradient(to right, hsl(var(--border) / .6) 1px, transparent 1px),
              linear-gradient(to bottom, hsl(var(--border) / .6) 1px, transparent 1px);
            background-size:28px 28px;
            -webkit-mask-image:radial-gradient(ellipse at 30% 0%, black 20%, transparent 70%);
            mask-image:radial-gradient(ellipse at 30% 0%, black 20%, transparent 70%);
        }}
        .rs-hero > * {{ position:relative; z-index:1; }}
        .rs-badge {{
            display:inline-block; padding:5px 12px; border-radius:8px;
            background:hsl(var(--violet) / .14); color:hsl(var(--violet));
            border:1px solid hsl(var(--violet) / .3);
            font-family:'JetBrains Mono',monospace; font-size:.68rem;
            letter-spacing:2px; font-weight:600; margin-bottom:18px; text-transform:uppercase;
        }}
        .rs-hero h1 {{ font-size:2.9rem; margin:0; line-height:1.04;
            background:var(--grad-text); -webkit-background-clip:text;
            background-clip:text; -webkit-text-fill-color:transparent; }}
        .rs-hero p {{ color:hsl(var(--muted)) !important; font-size:1.12rem;
            margin:.7rem 0 0; max-width:660px; }}

        .rs-card {{
            position:relative; overflow:hidden; height:100%;
            background:hsl(var(--card) / .6); border:1px solid hsl(var(--border));
            border-radius:18px; padding:22px;
            box-shadow:0 0 0 1px hsl(var(--border) / .6), 0 20px 60px -30px rgba(0,0,0,.5);
            backdrop-filter:blur(16px);
            transition:transform .18s ease, border-color .2s ease;
            animation: fadeIn .5s ease both;
        }}
        .rs-card::after {{
            content:""; position:absolute; top:-48px; right:-48px; width:128px; height:128px;
            border-radius:50%; filter:blur(40px); opacity:.5;
            background:radial-gradient(closest-side, hsl(var(--cyan) / .45), transparent);
        }}
        .rs-card:hover {{ transform:translateY(-4px); border-color:hsl(var(--primary) / .4); }}
        .rs-card .rs-ico {{ font-size:1.6rem; position:relative; z-index:1; }}
        .rs-card h3 {{ margin:.55rem 0 .3rem; font-size:1.05rem; position:relative; z-index:1; }}
        .rs-card p {{ margin:0; color:hsl(var(--muted)) !important; font-size:.9rem;
            line-height:1.55; position:relative; z-index:1; }}

        .rs-stat {{
            position:relative; overflow:hidden;
            background:hsl(var(--card) / .6); border:1px solid hsl(var(--border));
            border-radius:16px; padding:18px 20px;
            box-shadow:0 20px 60px -30px rgba(0,0,0,.5); backdrop-filter:blur(14px);
            animation: fadeIn .5s ease both;
        }}
        .rs-stat .rs-blob {{ position:absolute; top:-40px; right:-40px; width:110px; height:110px;
            border-radius:50%; filter:blur(36px); opacity:.55; }}
        .rs-stat .rs-val {{ font-family:'Space Grotesk',sans-serif; font-size:1.9rem;
            font-weight:600; line-height:1; letter-spacing:-.5px; position:relative; z-index:1; }}
        .rs-stat .rs-lbl {{ color:hsl(var(--muted)) !important; font-size:.68rem;
            font-weight:600; margin-top:8px; text-transform:uppercase; letter-spacing:1.5px;
            font-family:'JetBrains Mono',monospace; position:relative; z-index:1; }}

        .rs-section {{ display:flex; align-items:center; gap:12px; margin:8px 0 2px; }}
        .rs-section h3 {{ margin:0; font-size:1.05rem; text-transform:uppercase;
            letter-spacing:1px; font-family:'JetBrains Mono',monospace !important; font-weight:600; }}
        .rs-section .line {{ flex:1; height:1px;
            background:linear-gradient(90deg, hsl(var(--border)), transparent); }}

        .rs-pill {{ display:inline-flex; align-items:center; gap:7px; padding:5px 13px;
            border-radius:999px; font-size:.72rem; font-weight:600;
            font-family:'JetBrains Mono',monospace; text-transform:uppercase; letter-spacing:1px; }}
        .rs-dot {{ width:8px; height:8px; border-radius:50%; display:inline-block;
            animation: pulseGlow 2s infinite; }}

        @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(10px); }}
                            to {{ opacity:1; transform:translateY(0); }} }}
        @keyframes pulseGlow {{ 0%,100% {{ box-shadow:0 0 0 0 currentColor; }}
                                50% {{ box-shadow:0 0 12px 3px currentColor; }} }}

        .rs-footer {{ text-align:center; color:hsl(var(--muted)) !important; font-size:.78rem;
            font-family:'JetBrains Mono',monospace; letter-spacing:.5px;
            margin-top:36px; padding-top:16px; border-top:1px solid hsl(var(--border)); }}

        /* ---- Sidebar nav (observability-style) ---- */
        [data-testid="stSidebar"] .stButton > button {{
            justify-content:flex-start !important; text-align:left !important;
            background:transparent !important; border:1px solid transparent !important;
            color:hsl(var(--muted)) !important; font-weight:500 !important;
            box-shadow:none !important; padding:.5rem .8rem !important; border-radius:12px !important;
        }}
        [data-testid="stSidebar"] .stButton > button p {{ justify-content:flex-start; }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background:hsl(var(--alt) / .7) !important; color:hsl(var(--text)) !important;
            transform:none !important; border-color:hsl(var(--border)) !important; }}
        /* Active nav item = a sidebar "primary" button (subtle, not the loud CTA gradient) */
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
            background:hsl(var(--violet) / .16) !important; color:hsl(var(--text)) !important;
            border:1px solid hsl(var(--violet) / .35) !important;
            box-shadow:inset 3px 0 0 0 hsl(var(--violet)) !important; font-weight:600 !important; }}
        [data-testid="stSidebar"] hr {{ border-color:hsl(var(--border)); }}

        /* ---- Topbar ---- */
        .rs-topbar {{ display:flex; align-items:center; gap:14px; margin-bottom:18px; }}
        .rs-search {{ flex:1; display:flex; align-items:center; gap:10px;
            background:hsl(var(--card) / .6); border:1px solid hsl(var(--border));
            border-radius:12px; padding:9px 14px; color:hsl(var(--muted));
            font-size:.85rem; backdrop-filter:blur(10px); }}
        .rs-kbd {{ margin-left:auto; font-family:'JetBrains Mono',monospace; font-size:.7rem;
            background:hsl(var(--alt)); border:1px solid hsl(var(--border));
            border-radius:6px; padding:1px 6px; color:hsl(var(--muted)); }}
        .rs-avatar {{ width:34px; height:34px; border-radius:50%; flex:0 0 auto;
            display:flex; align-items:center; justify-content:center; color:#fff;
            font-weight:700; font-size:.8rem; background:var(--grad-brand);
            box-shadow:0 0 16px -4px hsl(var(--violet) / .8); }}

        /* ---- KPI metric tile (with delta pill) ---- */
        .rs-mtile {{ position:relative; overflow:hidden; height:100%;
            background:hsl(var(--card) / .6); border:1px solid hsl(var(--border));
            border-radius:18px; padding:18px 20px; backdrop-filter:blur(16px);
            box-shadow:0 20px 60px -32px rgba(0,0,0,.6);
            transition:border-color .2s ease, transform .15s ease;
            animation: fadeIn .5s ease both; }}
        .rs-mtile:hover {{ transform:translateY(-3px); border-color:hsl(var(--primary) / .4); }}
        .rs-mtile .blob {{ position:absolute; top:-46px; right:-46px; width:128px; height:128px;
            border-radius:50%; filter:blur(40px); opacity:.55; }}
        .rs-mtile .top {{ display:flex; align-items:flex-start; justify-content:space-between;
            position:relative; z-index:1; }}
        .rs-mtile .lbl {{ text-transform:uppercase; letter-spacing:1.6px; font-size:.66rem;
            font-family:'JetBrains Mono',monospace; color:hsl(var(--muted)); font-weight:600; }}
        .rs-mtile .val {{ font-family:'Space Grotesk',sans-serif; font-size:2rem; font-weight:600;
            letter-spacing:-.5px; margin-top:8px; }}
        .rs-mtile .ico {{ width:36px; height:36px; border-radius:10px; display:flex;
            align-items:center; justify-content:center; font-size:1rem;
            background:hsl(var(--alt) / .8); border:1px solid hsl(var(--border)); }}
        .rs-delta {{ display:inline-flex; align-items:center; gap:4px; margin-top:12px;
            padding:3px 9px; border-radius:8px; font-size:.72rem; font-weight:600;
            position:relative; z-index:1; }}
        .rs-delta.up {{ background:hsl(142 71% 45% / .15); color:hsl(142 71% 52%); }}
        .rs-delta.down {{ background:hsl(0 84% 60% / .15); color:hsl(0 84% 64%); }}
        .rs-delta.neutral {{ background:hsl(var(--violet) / .15); color:hsl(var(--violet)); }}

        /* ---- Chart cards = bordered containers styled as glass ---- */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background:hsl(var(--card) / .55) !important; border:1px solid hsl(var(--border)) !important;
            border-radius:18px !important; padding:6px 6px 2px !important;
            backdrop-filter:blur(14px); box-shadow:0 20px 60px -34px rgba(0,0,0,.55);
            transition:border-color .2s ease; }}
        [data-testid="stVerticalBlockBorderWrapper"]:hover {{ border-color:hsl(var(--primary) / .35) !important; }}
        .rs-chart-h {{ display:flex; align-items:center; justify-content:space-between;
            padding:6px 10px 2px; }}
        .rs-chart-h .t {{ display:flex; align-items:center; gap:8px; font-weight:600;
            font-size:.92rem; }}
        .rs-chart-h .v {{ font-family:'JetBrains Mono',monospace; font-size:.72rem; font-weight:600;
            padding:2px 9px; border-radius:8px; }}

        /* ---- Landing navbar ---- */
        .rs-navbar {{ display:flex; align-items:center; gap:10px; padding:6px 0 2px; }}
        .rs-brand {{ display:flex; align-items:center; gap:10px; font-weight:700;
            font-family:'Space Grotesk',sans-serif; font-size:1.05rem; }}
        .rs-logo {{ width:34px; height:34px; border-radius:11px; display:flex;
            align-items:center; justify-content:center; font-size:1.1rem;
            background:var(--grad-brand); box-shadow:0 0 18px -4px hsl(var(--violet) / .9); }}
        .rs-navlinks {{ flex:1; display:flex; justify-content:center; gap:26px; }}
        .rs-navlinks a {{ color:hsl(var(--muted)); font-size:.9rem; font-weight:500;
            text-decoration:none; transition:color .15s ease; cursor:pointer; }}
        .rs-navlinks a:hover {{ color:hsl(var(--text)); }}
        /* Smooth in-page scrolling for the landing nav anchors */
        html, body, section.main, [data-testid="stMain"],
        [data-testid="stAppViewContainer"] {{ scroll-behavior:smooth; }}
        .rs-anchor {{ display:block; height:0; scroll-margin-top:80px; }}

        /* ---- Browser mockup (home preview) ---- */
        .rs-browser {{ margin-top:12px; border-radius:18px; overflow:hidden;
            border:1px solid hsl(var(--border)); background:hsl(var(--card) / .7);
            box-shadow:0 40px 100px -40px hsl(var(--violet) / .6); backdrop-filter:blur(16px);
            animation: fadeIn .7s ease both; }}
        .rs-browser .bar {{ display:flex; align-items:center; gap:8px; padding:11px 14px;
            border-bottom:1px solid hsl(var(--border)); }}
        .rs-browser .bar i {{ width:11px; height:11px; border-radius:50%; display:inline-block; }}
        .rs-browser .url {{ margin:0 auto; font-family:'JetBrains Mono',monospace;
            font-size:.72rem; color:hsl(var(--muted)); }}
        .rs-browser .body {{ padding:18px; display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
        .rs-mini {{ background:hsl(var(--alt) / .5); border:1px solid hsl(var(--border));
            border-radius:12px; padding:12px 14px; }}
        .rs-mini .l {{ font-size:.6rem; text-transform:uppercase; letter-spacing:1.2px;
            font-family:'JetBrains Mono',monospace; color:hsl(var(--muted)); }}
        .rs-mini .n {{ font-family:'Space Grotesk',sans-serif; font-size:1.5rem; font-weight:600; margin-top:4px; }}

        /* ---- Social buttons (auth) ---- */
        .rs-oauth .stButton > button {{ background:hsl(var(--alt) / .6) !important;
            border:1px solid hsl(var(--border)) !important; font-weight:600 !important; }}

        /* ---- Testimonial panel (auth right side) ---- */
        .rs-quote {{ height:100%; min-height:420px; display:flex; flex-direction:column;
            justify-content:center; border-radius:22px; padding:40px 34px;
            background:
              radial-gradient(600px 300px at 80% 10%, hsl(var(--violet) / .22), transparent 60%),
              radial-gradient(500px 300px at 10% 90%, hsl(var(--cyan) / .18), transparent 60%),
              hsl(var(--card) / .6);
            border:1px solid hsl(var(--border)); backdrop-filter:blur(16px); }}
        .rs-quote .ey {{ text-align:center; text-transform:uppercase; letter-spacing:2px;
            font-family:'JetBrains Mono',monospace; font-size:.7rem; color:hsl(var(--muted)); margin-bottom:22px; }}
        .rs-quote .q {{ text-align:center; font-family:'Space Grotesk',sans-serif; font-size:1.7rem;
            font-weight:600; line-height:1.3; }}
        .rs-quote .q b {{ background:var(--grad-text); -webkit-background-clip:text;
            background-clip:text; -webkit-text-fill-color:transparent; }}
        .rs-quote .who {{ display:flex; align-items:center; gap:12px; justify-content:center; margin-top:26px; }}

        /* Alert / all-clear banners (dashboard alerts panel) */
        .alert-box {{
            position:relative; overflow:hidden;
            background:hsl(var(--card) / .7); border:1px solid hsl(0 84% 60% / .4);
            color:hsl(var(--text)) !important; padding:12px 16px; border-radius:14px;
            margin-bottom:8px; font-weight:600; backdrop-filter:blur(10px);
            box-shadow:0 0 24px -8px hsl(0 84% 60% / .6);
            animation: fadeIn .4s ease both;
        }}
        .ok-box {{
            background:hsl(var(--card) / .7); border:1px solid hsl(142 71% 45% / .4);
            color:hsl(var(--text)) !important; padding:12px 16px; border-radius:14px;
            font-weight:600; backdrop-filter:blur(10px);
            box-shadow:0 0 24px -10px hsl(142 71% 45% / .5);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# HTML component helpers (return strings to feed st.markdown)
# ===========================================================================
def hero(title: str, subtitle: str, badge: str = "") -> str:
    """A neon hero banner with a grid overlay and gradient-text title."""
    badge_html = f"<div class='rs-badge'>{badge}</div>" if badge else ""
    return (f"<div class='rs-hero'>{badge_html}"
            f"<h1>{title}</h1><p>{subtitle}</p></div>")


def feature_card(icon: str, title: str, desc: str) -> str:
    """A glass feature card with a corner glow-blob (icon + title + desc)."""
    return (f"<div class='rs-card'><div class='rs-ico'>{icon}</div>"
            f"<h3>{title}</h3><p>{desc}</p></div>")


def stat_card(value, label: str, color: str = PRIMARY, icon: str = "") -> str:
    """A cockpit stat tile with an accent glow-blob and uppercase label."""
    ic = f"{icon} " if icon else ""
    return (f"<div class='rs-stat'>"
            f"<div class='rs-blob' style='background:radial-gradient(closest-side,{color}88,transparent)'></div>"
            f"<div class='rs-val' style='color:{color}'>{ic}{value}</div>"
            f"<div class='rs-lbl'>{label}</div></div>")


def section_header(title: str) -> str:
    """A monospace uppercase section title with a fading divider line."""
    return f"<div class='rs-section'><h3>{title}</h3><span class='line'></span></div>"


def status_pill(text: str, color: str, live: bool = False) -> str:
    """A neon status pill with an optional pulsing dot."""
    dot = f"<span class='rs-dot' style='color:{color};background:{color}'></span>" if live else ""
    return (f"<span class='rs-pill' style='background:{color}1f;color:{color};"
            f"border:1px solid {color}44'>{dot}{text}</span>")


def footer(text: str) -> str:
    """A subtle centred monospace footer line."""
    return f"<div class='rs-footer'>{text}</div>"


# ---------------------------------------------------------------------------
# Observability-dashboard components
# ---------------------------------------------------------------------------
def topbar(status_text: str, status_color: str, avatar: str,
           live: bool = True) -> str:
    """A dashboard top bar: search box + status pill + user avatar."""
    dot = (f"<span class='rs-dot' style='color:{status_color};"
           f"background:{status_color}'></span>") if live else ""
    return (
        "<div class='rs-topbar'>"
        "<div class='rs-search'>🔎 Search hazards, roads, detections…"
        "<span class='rs-kbd'>⌘K</span></div>"
        f"<span class='rs-pill' style='background:{status_color}1f;color:{status_color};"
        f"border:1px solid {status_color}44'>{dot}{status_text}</span>"
        f"<div class='rs-avatar'>{avatar}</div>"
        "</div>"
    )


def metric_tile(label: str, value, delta_text: str = "", delta_kind: str = "neutral",
                icon: str = "•", accent: str = PRIMARY) -> str:
    """
    A KPI tile matching the RootSense metric card: uppercase mono label, big
    display value, an icon chip, a corner glow-blob and a coloured delta pill.

    delta_kind: 'up' (green), 'down' (red) or 'neutral' (violet).
    """
    arrow = {"up": "▲", "down": "▼", "neutral": ""}.get(delta_kind, "")
    delta = (f"<div class='rs-delta {delta_kind}'>{arrow} {delta_text}</div>"
             if delta_text else "")
    return (
        f"<div class='rs-mtile'>"
        f"<div class='blob' style='background:radial-gradient(closest-side,{accent}88,transparent)'></div>"
        f"<div class='top'><div><div class='lbl'>{label}</div>"
        f"<div class='val'>{value}</div></div>"
        f"<div class='ico'>{icon}</div></div>"
        f"{delta}</div>"
    )


def chart_header(title: str, icon: str, badge_text: str, badge_color: str) -> str:
    """Header row for a chart card (title left, coloured value badge right)."""
    return (
        f"<div class='rs-chart-h'><div class='t'>{icon} {title}</div>"
        f"<div class='v' style='background:{badge_color}1f;color:{badge_color}'>"
        f"{badge_text}</div></div>"
    )


def browser_mockup(tiles: list[tuple[str, str]], url: str = "roadsense.ai/dashboard") -> str:
    """
    A macOS-style browser frame previewing a mini dashboard (home page hero).
    `tiles` is a list of (label, value) shown as small metric cards.
    """
    mini = "".join(
        f"<div class='rs-mini'><div class='l'>{lbl}</div>"
        f"<div class='n'>{val}</div></div>" for lbl, val in tiles
    )
    return (
        "<div class='rs-browser'>"
        "<div class='bar'>"
        "<i style='background:#ff5f57'></i><i style='background:#febc2e'></i>"
        "<i style='background:#28c840'></i>"
        f"<span class='url'>{url}</span></div>"
        f"<div class='body'>{mini}</div></div>"
    )


def testimonial(quote_html: str, name: str, role: str, initials: str,
                eyebrow: str = "Why drivers trust RoadSense AI") -> str:
    """A gradient testimonial panel for the auth split-screen right side."""
    return (
        f"<div class='rs-quote'><div class='ey'>{eyebrow}</div>"
        f"<div class='q'>{quote_html}</div>"
        f"<div class='who'><div class='rs-avatar'>{initials}</div>"
        f"<div><div style='font-weight:700'>{name}</div>"
        f"<div style='color:hsl(var(--muted));font-size:.85rem'>{role}</div></div></div></div>"
    )


def area_chart(df, x: str, y: str, color: str, height: int = 150):
    """
    Build a neon gradient area chart (Altair) matching the RootSense look:
    filled area fading to transparent, a bright stroke, minimal axes.
    """
    import altair as alt

    base = alt.Chart(df)
    grad = alt.Gradient(
        gradient="linear",
        stops=[alt.GradientStop(color=color, offset=0),
               alt.GradientStop(color=color, offset=1)],
        x1=1, x2=1, y1=0, y2=1,
    )
    area = base.mark_area(
        line={"color": color, "strokeWidth": 2},
        color=alt.Gradient(
            gradient="linear",
            stops=[alt.GradientStop(color=color, offset=0),
                   alt.GradientStop(color="rgba(0,0,0,0)", offset=1)],
            x1=1, x2=1, y1=0, y2=1,
        ),
        opacity=0.5,
    ).encode(
        x=alt.X(f"{x}:Q", axis=alt.Axis(labels=False, ticks=False, title=None,
                                        grid=False, domain=False)),
        y=alt.Y(f"{y}:Q", axis=alt.Axis(labelColor="#8b8fa3", title=None,
                                        gridColor="rgba(255,255,255,0.05)",
                                        domain=False, tickCount=4)),
    )
    return area.properties(height=height).configure_view(
        strokeWidth=0, fill="rgba(0,0,0,0)"
    ).configure(background="rgba(0,0,0,0)")


def bar_chart(df, x: str, y: str, color: str, height: int = 150):
    """A neon vertical bar chart (Altair) with rounded caps and no chrome."""
    import altair as alt

    chart = alt.Chart(df).mark_bar(
        cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=color, opacity=0.85,
    ).encode(
        x=alt.X(f"{x}:N", axis=alt.Axis(labelColor="#8b8fa3", title=None,
                                        domain=False, ticks=False,
                                        labelAngle=0)),
        y=alt.Y(f"{y}:Q", axis=alt.Axis(labelColor="#8b8fa3", title=None,
                                        gridColor="rgba(255,255,255,0.05)",
                                        domain=False, tickCount=4)),
    )
    return chart.properties(height=height).configure_view(
        strokeWidth=0, fill="rgba(0,0,0,0)"
    ).configure(background="rgba(0,0,0,0)")
