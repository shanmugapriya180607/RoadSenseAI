"""
auth.py
=======
Authentication + public pages (Home / Login / Sign Up) for RoadSense AI.

Provides a real, offline sign-in experience like other apps:
  * User accounts are stored in a local SQLite database (`database/users.db`).
  * Passwords are NEVER stored in plain text — they are salted and hashed with
    PBKDF2-HMAC-SHA256 (Python standard library, no extra dependency).
  * A demo account (config.DEMO_USERNAME / DEMO_PASSWORD) is seeded on first
    run so judges can log in instantly.

This module also renders the public-facing Streamlit views:
  * render_home()   — official-style landing page (hero, features, CTA)
  * render_login()  — sign-in form
  * render_signup() — create-account form
  * top_nav()       — simple top navigation for logged-out visitors

The dashboard (dashboard.py) imports these and gates itself behind login.
"""

import hashlib
import hmac
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st

import config
import ui

# PBKDF2 parameters — 200k iterations is a sensible offline default.
_PBKDF2_ITERATIONS = 200_000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ===========================================================================
# Password hashing helpers (standard library only)
# ===========================================================================
def hash_password(password: str, salt: bytes | None = None) -> str:
    """
    Hash a password with a random salt using PBKDF2-HMAC-SHA256.

    Returns a single string "salt_hex$hash_hex" that is safe to store.
    """
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt,
                             _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Return True if `password` matches a stored "salt$hash" string."""
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                        salt, _PBKDF2_ITERATIONS)
        # Constant-time comparison to avoid timing attacks.
        return hmac.compare_digest(candidate.hex(), hash_hex)
    except Exception:
        return False


# ===========================================================================
# User database
# ===========================================================================
class UserAuth:
    """SQLite-backed user store with register / authenticate methods."""

    def __init__(self, db_path: Path = config.USERS_DB_PATH):
        """Open (creating if needed) the users database and seed a demo user."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_table()
        self._seed_demo_user()

    def _create_table(self) -> None:
        """Create the users table if it does not exist."""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                email         TEXT,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def _seed_demo_user(self) -> None:
        """Create the demo login on first run (idempotent)."""
        if not self.user_exists(config.DEMO_USERNAME):
            self.register(config.DEMO_USERNAME, config.DEMO_PASSWORD,
                          email="demo@roadsense.ai")

    # ------------------------------------------------------------------ #
    def user_exists(self, username: str) -> bool:
        """Return True if a username is already taken."""
        row = self.conn.execute(
            "SELECT 1 FROM users WHERE username = ?", (username.strip().lower(),)
        ).fetchone()
        return row is not None

    def register(self, username: str, password: str,
                 email: str = "") -> tuple[bool, str]:
        """
        Create a new account.

        Returns (success, message). Validates uniqueness and basic strength.
        """
        username = username.strip().lower()
        if not username:
            return False, "Username cannot be empty."
        if len(password) < 6:
            return False, "Password must be at least 6 characters."
        if email and not _EMAIL_RE.match(email):
            return False, "Please enter a valid email address."
        if self.user_exists(username):
            return False, "That username is already taken."

        self.conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (username, email.strip(), hash_password(password),
             datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()
        return True, "Account created! You can now sign in."

    def authenticate(self, username: str, password: str) -> bool:
        """Return True if the username/password pair is valid."""
        row = self.conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
        if row is None:
            return False
        return verify_password(password, row["password_hash"])


# ===========================================================================
# Streamlit session helpers
# ===========================================================================
def init_auth_state() -> None:
    """Initialise auth-related session_state keys and the UserAuth backend."""
    if "auth" not in st.session_state:
        st.session_state.auth = UserAuth()
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "page" not in st.session_state:
        st.session_state.page = "home"   # home | login | signup


def go(page: str) -> None:
    """Navigate to a public page and rerun."""
    st.session_state.page = page
    st.rerun()


def login_user(username: str) -> None:
    """Mark the session as authenticated and jump into the dashboard."""
    st.session_state.authenticated = True
    st.session_state.username = username.strip().lower()
    st.rerun()


def logout_user() -> None:
    """Sign the current user out and return to the home page."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.page = "home"
    st.rerun()


# Small reusable HTML snippets --------------------------------------------
_BRAND = ("<div class='rs-brand'><div class='rs-logo'>🛰️</div>"
          f"{config.APP_NAME}</div>")


def _theme_btn(col) -> None:
    """A small light/dark toggle button placed in the given column."""
    if col.button("☀️" if ui.is_dark() else "🌙", use_container_width=True,
                  help="Toggle light / dark theme"):
        ui.toggle_theme()


# ===========================================================================
# Public page: Home / landing (RootSense-style hero + browser preview)
# ===========================================================================
def render_home() -> None:
    """Full-screen landing hero with a live dashboard preview mockup."""
    ui.inject_theme()

    # Real, current numbers power the preview mockup (read-only).
    from database import RoadMemoryDB, seed_sample_data
    db = RoadMemoryDB()
    seed_sample_data(db)                     # only seeds if empty (idempotent)
    counts = db.counts_by_type()
    total = db.count()
    df = db.get_all_hazards()
    avg = float(df["confidence"].mean()) if not df.empty else 0.0

    # ---- Top navbar ----
    nav = st.columns([3, 0.9, 1.3, 0.5])
    nav[0].markdown(
        "<div class='rs-navbar'>" + _BRAND +
        "<div class='rs-navlinks'>"
        "<a href='#sec-features'>Features</a>"
        "<a href='#sec-preview'>Dashboard</a>"
        "<a href='#sec-how'>How it works</a>"
        "<a href='#sec-safety'>Safety</a></div></div>",
        unsafe_allow_html=True)
    if nav[1].button("Log in", use_container_width=True):
        go("login")
    if nav[2].button("Open dashboard →", type="primary", use_container_width=True):
        go("login")
    _theme_btn(nav[3])

    # ---- Hero ----
    st.markdown(
        "<div style='text-align:center;max-width:920px;margin:36px auto 24px'>"
        "<div class='rs-badge'>✦ NEW · REAL-TIME HAZARD DETECTION</div>"
        "<h1 style='font-size:3.4rem;line-height:1.05;margin:.3rem 0'>"
        "Detect road hazards in<br>"
        "<span style='background:var(--grad-text);-webkit-background-clip:text;"
        "background-clip:text;-webkit-text-fill-color:transparent'>"
        "seconds, not surprises.</span></h1>"
        "<p style='color:hsl(var(--muted));font-size:1.14rem;max-width:660px;"
        "margin:16px auto 0'>RoadSense AI watches the road through your camera, "
        "detects potholes, cracks and speed breakers, then remembers where they "
        "are — and warns you before you hit them again. Built for safer drives.</p>"
        "</div>",
        unsafe_allow_html=True)

    # ---- CTA buttons (centred) ----
    c = st.columns([1.25, 1, 1, 1.25])
    if c[1].button("🚀 Try the live demo", type="primary", use_container_width=True):
        go("login")
    if c[2].button("🤖 Talk to RoadSense AI", use_container_width=True):
        go("login")
    st.markdown(
        "<div style='text-align:center;color:hsl(var(--muted));font-size:.78rem;"
        "margin-top:8px;font-family:JetBrains Mono,monospace'>"
        "100% local inference · No cloud · Works offline</div>",
        unsafe_allow_html=True)

    # ---- Live dashboard preview (browser mockup with REAL counts) ----
    st.markdown("<span id='sec-preview' class='rs-anchor'></span>",
                unsafe_allow_html=True)
    st.markdown(
        ui.browser_mockup([
            ("Total Hazards", str(total)),
            ("Potholes", str(counts.get("pothole", 0))),
            ("Cracks", str(counts.get("crack", 0))),
            ("AI Confidence", f"{avg:.2f}"),
        ]),
        unsafe_allow_html=True)

    # ---- Features ----
    st.write("")
    st.markdown("<span id='sec-features' class='rs-anchor'></span>",
                unsafe_allow_html=True)
    st.markdown(ui.section_header("Features"), unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    f1.markdown(ui.feature_card(
        "🎯", "Real-time Detection",
        "YOLOv8 spots potholes, cracks and speed breakers from your webcam or a "
        "road video — entirely on your laptop."), unsafe_allow_html=True)
    f2.markdown(ui.feature_card(
        "🧠", "Road Memory",
        "Every hazard is saved with a GPS location in a local database, so your "
        "vehicle never forgets a bad stretch of road."), unsafe_allow_html=True)
    f3.markdown(ui.feature_card(
        "🔊", "Driver Alerts",
        "Come within 30 m of a known hazard and RoadSense warns you with a popup "
        "and a spoken alert."), unsafe_allow_html=True)

    # ---- How it works ----
    st.write("")
    st.markdown("<span id='sec-how' class='rs-anchor'></span>",
                unsafe_allow_html=True)
    st.markdown(ui.section_header("How it works"), unsafe_allow_html=True)
    h1, h2, h3 = st.columns(3)
    h1.markdown(ui.feature_card(
        "1️⃣", "Watch the road",
        "Point your camera at the road (or load a video). The on-device model "
        "analyses every frame in real time."), unsafe_allow_html=True)
    h2.markdown(ui.feature_card(
        "2️⃣", "Remember hazards",
        "Each detection is tagged with a simulated GPS location and stored in "
        "your local road memory — no duplicates."), unsafe_allow_html=True)
    h3.markdown(ui.feature_card(
        "3️⃣", "Get warned",
        "Approach a known hazard again and RoadSense alerts you before you reach "
        "it, so you can slow down in time."), unsafe_allow_html=True)

    # ---- Safety & privacy ----
    st.write("")
    st.markdown("<span id='sec-safety' class='rs-anchor'></span>",
                unsafe_allow_html=True)
    st.markdown(ui.section_header("Safety & privacy"), unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    s1.markdown(ui.stat_card("100%", "On-device inference", ui.NEON_LIME, "🔒"),
                unsafe_allow_html=True)
    s2.markdown(ui.stat_card("0", "Frames sent to cloud", ui.NEON_CYAN, "☁️"),
                unsafe_allow_html=True)
    s3.markdown(ui.stat_card("~30 m", "Early-warning radius", ui.NEON_VIOLET, "📡"),
                unsafe_allow_html=True)
    st.markdown(
        ui.feature_card(
            "🛡️", "Offline-first by design",
            "RoadSense runs entirely on your laptop. No video ever leaves your "
            "device — detection, storage and alerts are all local. Optional cloud "
            "sync is intentionally left disabled."),
        unsafe_allow_html=True)

    st.markdown(
        ui.footer("RoadSense AI · Edge-AI road hazard detection · offline-first · "
                  "no video ever leaves your device."),
        unsafe_allow_html=True)


# ===========================================================================
# Shared split-screen auth layout
# ===========================================================================
def _auth_topbar() -> None:
    """Brand on the left, Home + theme toggle on the right."""
    t = st.columns([3, 0.7, 0.5])
    t[0].markdown(f"<div class='rs-navbar'>{_BRAND}</div>", unsafe_allow_html=True)
    if t[1].button("← Home", use_container_width=True):
        go("home")
    _theme_btn(t[2])
    st.write("")


def _oauth_buttons() -> None:
    """Google sign-in button (UI-only demo for the prototype)."""
    if st.button("🔴  Continue with Google", use_container_width=True):
        st.info("Social sign-in is a UI demo for the prototype — "
                "please use the form below.")
    st.markdown(
        "<div style='text-align:center;color:hsl(var(--muted));font-size:.7rem;"
        "letter-spacing:2px;margin:12px 0;font-family:JetBrains Mono,monospace'>"
        "OR</div>", unsafe_allow_html=True)


# ===========================================================================
# Public page: Login (split screen)
# ===========================================================================
def render_login() -> None:
    """Sign-in split screen: form (left) + testimonial (right)."""
    ui.inject_theme()
    _auth_topbar()

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown("## Welcome back")
        st.caption("Sign in to your RoadSense workspace.")
        _oauth_buttons()

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="admin")
            password = st.text_input("Password", type="password",
                                     placeholder="••••••••")
            submitted = st.form_submit_button("Sign in", use_container_width=True,
                                              type="primary")

        if submitted:
            auth: UserAuth = st.session_state.auth
            if auth.authenticate(username, password):
                st.success("Welcome back! Loading your dashboard…")
                login_user(username)
            else:
                st.error("Invalid username or password. Please try again.")

        st.info(f"👋 **Demo login** — username: `{config.DEMO_USERNAME}` · "
                f"password: `{config.DEMO_PASSWORD}`")
        if st.button("New here? Create an account →"):
            go("signup")

    with right:
        st.markdown(
            ui.testimonial(
                "“RoadSense flagged the pothole that <b>saved my tyre</b> — "
                "now it warns me every single drive.”",
                "Aarav Mehta", "Daily commuter · Bengaluru", "AM"),
            unsafe_allow_html=True)


# ===========================================================================
# Public page: Sign Up (split screen)
# ===========================================================================
def render_signup() -> None:
    """Create-account split screen: form (left) + testimonial (right)."""
    ui.inject_theme()
    _auth_topbar()

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown("## Create your workspace")
        st.caption("Start building your road memory — no setup required.")
        _oauth_buttons()

        with st.form("signup_form", clear_on_submit=False):
            r1 = st.columns(2)
            username = r1[0].text_input("Username", placeholder="your_name")
            email = r1[1].text_input("Email (optional)",
                                     placeholder="you@example.com")
            password = st.text_input("Password", type="password",
                                     placeholder="at least 6 characters")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create workspace",
                                              use_container_width=True,
                                              type="primary")

        if submitted:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                auth: UserAuth = st.session_state.auth
                ok, msg = auth.register(username, password, email)
                if ok:
                    st.success(msg)
                    st.info("Redirecting to sign in…")
                    go("login")
                else:
                    st.error(msg)

        if st.button("Already have an account? Sign in →"):
            go("login")

    with right:
        st.markdown(
            ui.testimonial(
                "“RoadSense remembers every bad patch of road so I "
                "<b>never get caught out twice.</b>”",
                "Priya Nair", "Fleet driver · Kochi", "PN"),
            unsafe_allow_html=True)
