"""
dashboard.py
============
RoadSense AI — Streamlit application entry point.

Run with:
    streamlit run dashboard.py

This is now a small multi-view app with real authentication:

    Home (landing)  →  Sign In / Sign Up  →  Dashboard (protected)

A visitor lands on an official-style home page, signs in (or creates an
account), and only then reaches the live dashboard. All of that is routed from
the bottom of this file; the heavy dashboard UI lives in render_dashboard().

The dashboard itself ties together every module:
  * detect.py         -> live hazard detection (webcam or video file)
  * gps_simulator.py  -> simulated moving vehicle
  * database.py       -> SQLite "road memory"
  * alert.py          -> proximity voice/visual warnings
  * map_utils.py      -> interactive Folium hazard map

EDGE-AI NOTE: all inference runs locally; no frame ever leaves the laptop.

Streamlit reruns the whole script on every interaction, so long-lived objects
(DB, detector, GPS, alert system, video source) are cached in st.session_state.
The live camera loop processes a small batch of frames per run and then calls
st.rerun(), which keeps the sidebar buttons responsive while still streaming.
"""

import time

import cv2
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import config
import auth
import ui
import assistant
from database import RoadMemoryDB, seed_sample_data
from gps_simulator import GPSSimulator
from alert import AlertSystem
from map_utils import build_hazard_map, map_to_html
from utils.video_source import VideoSource

# Detector is imported lazily (heavy ML dependency) only when the camera starts.


# ============================================================================
# Page / theme setup
# ============================================================================
st.set_page_config(
    page_title="RoadSense AI",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# The premium light/dark design system + all component styling lives in ui.py.
# (Injected per-render inside main() so the theme switch applies everywhere.)


# ============================================================================
# Session-state initialisation (persist heavy objects across reruns)
# ============================================================================
def init_state() -> None:
    """Create long-lived objects once and stash them in session_state."""
    if "db" not in st.session_state:
        db = RoadMemoryDB()
        seed_sample_data(db)          # populate a few demo hazards on first run
        st.session_state.db = db
    if "gps" not in st.session_state:
        st.session_state.gps = GPSSimulator()
    if "alert" not in st.session_state:
        st.session_state.alert = AlertSystem(voice=True)
    if "detector" not in st.session_state:
        st.session_state.detector = None   # created on first camera start
    if "video" not in st.session_state:
        st.session_state.video = None
    if "running" not in st.session_state:
        st.session_state.running = False
    if "recent_alerts" not in st.session_state:
        st.session_state.recent_alerts = []
    if "video_path" not in st.session_state:
        st.session_state.video_path = ""


# ============================================================================
# Helper functions (session-state only — safe at module level)
# ============================================================================
def get_detector():
    """Lazily construct the YOLO detector (first camera start only)."""
    if st.session_state.detector is None:
        with st.spinner("Loading AI model (first time may download weights)…"):
            from detect import HazardDetector
            st.session_state.detector = HazardDetector()
    return st.session_state.detector


def start_source(source) -> None:
    """Open a webcam index or video file and flip the app into running mode."""
    stop_source()  # release any existing source first
    st.session_state.video = VideoSource(source)
    if st.session_state.video.error:
        st.session_state.running = False
        st.error(st.session_state.video.error)
    else:
        st.session_state.running = True


def stop_source() -> None:
    """Stop the live loop and release the camera/video."""
    st.session_state.running = False
    if st.session_state.video is not None:
        st.session_state.video.release()
        st.session_state.video = None


def register_alerts(events: list[dict]) -> None:
    """Prepend new alert events to the recent-alerts log (keep last 8)."""
    for ev in events:
        st.session_state.recent_alerts.insert(
            0, f"⚠️ {ev['message']}  ({time.strftime('%H:%M:%S')})"
        )
    st.session_state.recent_alerts = st.session_state.recent_alerts[:8]


# ============================================================================
# Sidebar navigation (observability-style)
# ============================================================================
_NAV_ITEMS = [
    ("overview", "📊  Overview"),
    ("live", "🎥  Live Detection"),
    ("map", "🗺️  Hazard Map"),
    ("history", "🗂️  History"),
    ("assistant", "🤖  AI Assistant"),
]


def _sidebar_nav(db: RoadMemoryDB) -> str:
    """Render the sidebar nav and return the selected page key."""
    cur = st.session_state.get("nav", "overview")

    st.sidebar.markdown(
        "<div class='rs-brand' style='margin-bottom:0'>"
        "<div class='rs-logo'>🛰️</div>RoadSense AI</div>"
        "<div style='color:hsl(var(--muted));font-family:JetBrains Mono,monospace;"
        "font-size:.6rem;letter-spacing:2px;text-transform:uppercase;"
        "margin:2px 0 14px 44px'>Edge · Observability</div>",
        unsafe_allow_html=True,
    )

    badges = {"history": str(db.count()), "assistant": "AI"}
    for key, label in _NAV_ITEMS:
        badge = badges.get(key, "")
        text = f"{label}      {badge}" if badge else label
        if st.sidebar.button(
            text, key=f"nav_{key}", use_container_width=True,
            type="primary" if cur == key else "secondary",
        ):
            if key != "live":
                stop_source()      # release camera when leaving the live page
            st.session_state.nav = key
            st.rerun()

    st.sidebar.divider()
    c = st.sidebar.columns([1, 1])
    if c[0].button("☀️" if ui.is_dark() else "🌙", use_container_width=True,
                   help="Toggle theme"):
        ui.toggle_theme()
    if c[1].button("🚪 Logout", use_container_width=True):
        stop_source()
        auth.logout_user()

    st.sidebar.caption(f"Signed in as **{st.session_state.username}**")
    det = st.session_state.detector
    if det is not None:
        tag = "custom" if not det.using_fallback else "fallback"
        st.sidebar.caption(f"Model · `{det.model_name}` ({tag})")
    return cur


def _topbar() -> None:
    """Render the dashboard top bar (search + status pill + avatar)."""
    live = st.session_state.running
    avatar = str(st.session_state.username)[:2].upper()
    st.markdown(
        ui.topbar(
            "Monitoring live" if live else "All systems monitored",
            ui.SUCCESS, avatar, live=True,
        ),
        unsafe_allow_html=True,
    )


# ============================================================================
# Page: Overview (KPI tiles + neon charts)
# ============================================================================
def _page_overview(db: RoadMemoryDB, gps: GPSSimulator) -> None:
    counts = db.counts_by_type()
    total = db.count()
    df = db.get_all_hazards()

    # Heading with a LIVE pill.
    st.markdown(
        "<h2 style='margin:0 0 2px'>Road Safety Overview &nbsp;"
        f"{ui.status_pill('● LIVE', ui.NEON_LIME, live=True)}</h2>"
        "<div style='color:hsl(var(--muted));font-size:.86rem;margin-bottom:16px'>"
        "Local road memory · auto-updating · region simulated</div>",
        unsafe_allow_html=True,
    )

    # ---- KPI tiles ----
    today = 0
    if not df.empty:
        d = pd.to_datetime(df["timestamp"], errors="coerce").dt.date
        from datetime import date
        today = int((d == date.today()).sum())
    avg = float(df["confidence"].mean()) * 100 if not df.empty else 0.0

    def share(n):
        return f"{(n / total * 100):.0f}% of total" if total else "0%"

    k = st.columns(4)
    k[0].markdown(ui.metric_tile(
        "Total Hazards", total, f"{today} today", "up", "🛰️", ui.NEON_VIOLET),
        unsafe_allow_html=True)
    k[1].markdown(ui.metric_tile(
        "Potholes", counts.get("pothole", 0), share(counts.get("pothole", 0)),
        "neutral", "⚠️", ui.DANGER), unsafe_allow_html=True)
    k[2].markdown(ui.metric_tile(
        "Cracks", counts.get("crack", 0), share(counts.get("crack", 0)),
        "neutral", "🛣️", ui.WARNING), unsafe_allow_html=True)
    k[3].markdown(ui.metric_tile(
        "Avg Confidence", f"{avg:.0f}%", f"{total} detections", "up", "🎯",
        ui.NEON_CYAN), unsafe_allow_html=True)

    st.write("")

    # ---- Neon charts ----
    if df.empty:
        st.info("No hazards yet — open **Live Detection** to build your road memory.")
        return

    ordered = df.sort_values("id").reset_index(drop=True)
    growth = pd.DataFrame({"i": range(1, len(ordered) + 1),
                           "n": range(1, len(ordered) + 1)})
    conf = pd.DataFrame({"i": range(1, len(ordered) + 1),
                         "c": (ordered["confidence"] * 100).round(1)})
    by_type = (ordered["hazard_type"].value_counts().rename_axis("type")
               .reset_index(name="count"))
    by_type["type"] = by_type["type"].str.replace("_", " ").str.title()

    ch = st.columns(3)
    with ch[0]:
        with st.container(border=True):
            st.markdown(ui.chart_header("Road memory growth", "📈",
                        f"{total} total", ui.NEON_VIOLET), unsafe_allow_html=True)
            st.altair_chart(ui.area_chart(growth, "i", "n", ui.NEON_VIOLET),
                            use_container_width=True)
    with ch[1]:
        with st.container(border=True):
            top = by_type.iloc[0]["type"] if not by_type.empty else "—"
            st.markdown(ui.chart_header("Hazards by type", "📊", top, ui.NEON_CYAN),
                        unsafe_allow_html=True)
            st.altair_chart(ui.bar_chart(by_type, "type", "count", ui.NEON_CYAN),
                            use_container_width=True)
    with ch[2]:
        with st.container(border=True):
            st.markdown(ui.chart_header("Detection confidence", "🎯",
                        f"{avg:.0f}% avg", ui.NEON_PINK), unsafe_allow_html=True)
            st.altair_chart(ui.area_chart(conf, "i", "c", ui.NEON_PINK),
                            use_container_width=True)

    # ---- Recent detections feed ----
    st.write("")
    st.markdown(ui.section_header("Recent detections"), unsafe_allow_html=True)
    with st.container(border=True):
        recent = ordered.tail(6).iloc[::-1]
        rows = ""
        for _, r in recent.iterrows():
            col = ui.HAZARD_COLORS.get(r["hazard_type"], ui.PRIMARY)
            label = str(r["hazard_type"]).replace("_", " ").title()
            rows += (
                "<div style='display:flex;align-items:center;gap:12px;padding:10px 12px;"
                "border-bottom:1px solid hsl(var(--border))'>"
                f"<span class='rs-dot' style='color:{col};background:{col}'></span>"
                f"<b style='flex:0 0 130px'>{label}</b>"
                f"<span style='color:hsl(var(--muted));font-family:JetBrains Mono,monospace;"
                f"font-size:.78rem;flex:1'>{r['latitude']:.4f}, {r['longitude']:.4f}</span>"
                f"<span class='rs-pill' style='background:{col}1f;color:{col}'>"
                f"{(r['confidence'] * 100):.0f}%</span></div>")
        st.markdown(rows, unsafe_allow_html=True)


# ============================================================================
# Page: Live Detection (camera loop — unchanged detection logic)
# ============================================================================
def _page_live(db: RoadMemoryDB, gps: GPSSimulator) -> None:
    st.markdown(ui.section_header("🎥 Live Detection"), unsafe_allow_html=True)

    # Controls row.
    ctr = st.columns([1, 1, 2.4, 1])
    if ctr[0].button("▶ Start", type="primary", use_container_width=True):
        get_detector()
        start_source(config.DEFAULT_CAMERA_INDEX)
        st.rerun()
    if ctr[1].button("⏹ Stop", use_container_width=True):
        stop_source()
        st.rerun()
    vpath = ctr[2].text_input("Video path", value=st.session_state.video_path,
                              label_visibility="collapsed",
                              placeholder=r"Load a road video, e.g. dataset\road.mp4")
    if ctr[3].button("🎬 Load", use_container_width=True):
        st.session_state.video_path = vpath
        if vpath.strip():
            get_detector()
            start_source(vpath.strip())
            st.rerun()
        else:
            st.warning("Enter a valid video path first.")

    st.session_state.alert.voice = st.toggle(
        "🔊 Voice alerts", value=st.session_state.alert.voice)

    left, right = st.columns([1.3, 1])
    with left:
        frame_ph = st.empty()
        status_ph = st.empty()
    with right:
        st.markdown(ui.section_header("📍 Position"), unsafe_allow_html=True)
        pos_ph = st.empty()
        st.markdown(ui.section_header("🚨 Alerts"), unsafe_allow_html=True)
        alert_ph = st.empty()

    def render_position(lat, lon):
        pos_ph.markdown(ui.stat_card(f"{lat:.5f}", "Latitude", ui.NEON_CYAN)
                        + "<div style='height:8px'></div>"
                        + ui.stat_card(f"{lon:.5f}", "Longitude", ui.NEON_VIOLET),
                        unsafe_allow_html=True)

    def render_alerts():
        if st.session_state.recent_alerts:
            html = "".join(f"<div class='alert-box'>{a}</div>"
                           for a in st.session_state.recent_alerts)
        else:
            html = "<div class='ok-box'>✅ No hazards nearby. Drive safe!</div>"
        alert_ph.markdown(html, unsafe_allow_html=True)

    def run_live_batch(batch_frames: int = 12):
        detector = get_detector()
        video: VideoSource = st.session_state.video
        alert_system: AlertSystem = st.session_state.alert
        if video is None or not video.is_opened():
            st.session_state.running = False
            status_ph.error("Camera / video not available.")
            return
        for _ in range(batch_frames):
            if not st.session_state.running:
                break
            ok, frame = video.read()
            if not ok or frame is None:
                status_ph.warning("No frame received.")
                break
            lat, lon = gps.update()
            detections = detector.detect(frame)
            annotated = detector.draw(frame, detections)
            for det in detections:
                db.add_hazard(lat, lon, det["hazard_type"], det["confidence"])
            events = alert_system.check(lat, lon, db.get_hazards_as_dicts())
            if events:
                register_alerts(events)
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            frame_ph.image(rgb, channels="RGB", use_container_width=True)
            status_ph.info(f"Detections this frame: {len(detections)}  ·  "
                           f"Model: {detector.model_name}")
            render_position(lat, lon)
            render_alerts()
            time.sleep(0.03)

    if st.session_state.running:
        run_live_batch()
        st.rerun()
    else:
        frame_ph.info("Camera stopped. Press **Start** or **Load** a road video.")
        render_position(*gps.current())
        render_alerts()


# ============================================================================
# Page: Hazard Map
# ============================================================================
def _page_map(db: RoadMemoryDB, gps: GPSSimulator) -> None:
    st.markdown(ui.section_header("🗺️ Hazard Map"), unsafe_allow_html=True)
    lat, lon = gps.current()
    st.markdown(
        ui.status_pill(f"Vehicle · {lat:.4f}, {lon:.4f}", ui.NEON_CYAN, live=True),
        unsafe_allow_html=True)
    st.write("")
    fmap = build_hazard_map(db.get_all_hazards(), vehicle_pos=(lat, lon))
    components.html(map_to_html(fmap), height=560)


# ============================================================================
# Page: History (filters + table + export + clear)
# ============================================================================
def _page_history(db: RoadMemoryDB) -> None:
    st.markdown(ui.section_header("🗂️ Detection History"), unsafe_allow_html=True)
    df = db.get_all_hazards()
    if df.empty:
        st.info("No hazards recorded yet.")
        return

    fc1, fc2, fc3 = st.columns([1, 1, 1])
    types = ["All"] + sorted(df["hazard_type"].unique().tolist())
    chosen_type = fc1.selectbox("Hazard type", types)
    df["_date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date
    date_opts = ["All"] + [str(d) for d in sorted(df["_date"].dropna().unique())]
    chosen_date = fc2.selectbox("Date", date_opts)
    fc3.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if fc3.button("🗑 Clear road memory", use_container_width=True):
        db.clear()
        st.session_state.alert.reset()
        st.session_state.recent_alerts = []
        st.rerun()

    view = df.copy()
    if chosen_type != "All":
        view = view[view["hazard_type"] == chosen_type]
    if chosen_date != "All":
        view = view[view["_date"].astype(str) == chosen_date]

    with st.container(border=True):
        st.dataframe(view.drop(columns=["_date"]), use_container_width=True,
                     hide_index=True)

    st.download_button(
        "⬇ Download history as CSV",
        data=df.drop(columns=["_date"]).to_csv(index=False).encode("utf-8"),
        file_name="hazard_history.csv", mime="text/csv")


# ============================================================================
# Page: AI Assistant (offline chatbot over the road-memory data)
# ============================================================================
def _chat_process(question: str, db: RoadMemoryDB, gps: GPSSimulator) -> None:
    """Append the user's question and the assistant's answer to the log."""
    st.session_state.chat.append(("user", question))
    ans = assistant.answer(question, db.get_all_hazards(), gps.current())
    st.session_state.chat.append(("assistant", ans))


def _page_assistant(db: RoadMemoryDB, gps: GPSSimulator) -> None:
    st.markdown(ui.section_header("🤖 AI Assistant"), unsafe_allow_html=True)
    st.caption("Ask about your road memory — 100% offline, nothing leaves your device.")

    if "chat" not in st.session_state:
        st.session_state.chat = [(
            "assistant",
            "👋 Hi! I'm your **RoadSense assistant**. Ask me about your detected "
            "hazards — counts, the nearest one, the most common type, or a summary.",
        )]

    # Suggestion chips.
    chips = st.columns(len(assistant.SUGGESTIONS))
    for i, s in enumerate(assistant.SUGGESTIONS):
        if chips[i].button(s, key=f"sug_{i}", use_container_width=True):
            _chat_process(s, db, gps)
            st.rerun()

    # Conversation.
    for role, msg in st.session_state.chat:
        with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
            st.markdown(msg)

    prompt = st.chat_input("Ask about your hazards…")
    if prompt:
        _chat_process(prompt, db, gps)
        st.rerun()


# ============================================================================
# The protected dashboard view (sidebar nav + topbar + routed page)
# ============================================================================
def render_dashboard() -> None:
    """Render the observability-style dashboard (only reached once authed)."""
    init_state()
    if "nav" not in st.session_state:
        st.session_state.nav = "overview"

    db: RoadMemoryDB = st.session_state.db
    gps: GPSSimulator = st.session_state.gps

    nav = _sidebar_nav(db)
    _topbar()

    if nav == "live":
        _page_live(db, gps)
    elif nav == "map":
        _page_map(db, gps)
    elif nav == "history":
        _page_history(db)
    elif nav == "assistant":
        _page_assistant(db, gps)
    else:
        _page_overview(db, gps)

    st.markdown(
        ui.footer("RoadSense AI · Edge-AI hazard detection · offline-first · "
                  "© hackathon prototype"),
        unsafe_allow_html=True,
    )


# ============================================================================
# Router — Home / Login / Sign Up  →  Dashboard (protected)
# ============================================================================
def main() -> None:
    """Top-level router: gate the dashboard behind authentication."""
    ui.inject_theme()          # premium light/dark styling for every view
    auth.init_auth_state()

    if st.session_state.authenticated:
        render_dashboard()
        return

    # Logged-out visitors see the public pages.
    page = st.session_state.page
    if page == "login":
        auth.render_login()
    elif page == "signup":
        auth.render_signup()
    else:
        auth.render_home()


main()
