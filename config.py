"""
config.py
=========
Central configuration for RoadSense AI.

All tunable parameters, file paths, and constants live here so that no other
module needs hardcoded paths. Paths are built with `pathlib` relative to this
file, which keeps the project fully portable across machines and OSes
(Windows-first, but Linux/Mac friendly too).

Change values here to tweak behaviour without touching business logic.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Project directories (all resolved relative to this file's location)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

DATASET_DIR = BASE_DIR / "dataset"      # training / sample images & videos
MODELS_DIR = BASE_DIR / "models"        # YOLO weight files (.pt)
DATABASE_DIR = BASE_DIR / "database"    # SQLite database file lives here
DASHBOARD_DIR = BASE_DIR / "dashboard"  # dashboard assets (maps, exports)
UTILS_DIR = BASE_DIR / "utils"          # helper modules

# Ensure the directories that we WRITE to actually exist at runtime.
for _d in (DATASET_DIR, MODELS_DIR, DATABASE_DIR, DASHBOARD_DIR, UTILS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH = DATABASE_DIR / "road_memory.db"
DB_TABLE = "road_memory"

# Separate database for user accounts (authentication / sign-in).
USERS_DB_PATH = DATABASE_DIR / "users.db"

# A demo account is seeded on first run so judges can log in immediately.
# (Change or remove for any real deployment.)
DEMO_USERNAME = "admin"
DEMO_PASSWORD = "admin123"

# App identity (shown across the home / auth / dashboard pages).
APP_NAME = "RoadSense AI"
APP_TAGLINE = "Giving Memory to Vehicles"

# ---------------------------------------------------------------------------
# AI model
# ---------------------------------------------------------------------------
# Preferred custom-trained model. If this file does not exist, the detector
# gracefully falls back to a pretrained YOLOv8n model (auto-downloaded by
# Ultralytics on first use, or loaded from MODELS_DIR if present).
CUSTOM_MODEL_PATH = MODELS_DIR / "roadsense_yolov8n.pt"
FALLBACK_MODEL = "yolov8n.pt"  # Ultralytics pretrained (COCO)

# Minimum confidence for a detection to be accepted.
CONFIDENCE_THRESHOLD = 0.35

# The hazard classes our custom model is expected to output. When we fall
# back to the pretrained COCO model (which has none of these classes), we map
# a few COCO classes to "road hazard" so the demo still shows live detections.
HAZARD_CLASSES = ["pothole", "crack", "speed_breaker"]

# COCO class names that we treat as stand-in hazards for the fallback demo so
# that the pipeline visibly "works" without a custom model. Feel free to edit.
FALLBACK_HAZARD_MAP = {
    "stop sign": "pothole",
    "fire hydrant": "speed_breaker",
    "bench": "crack",
    "suitcase": "pothole",
    "backpack": "crack",
}

# ---------------------------------------------------------------------------
# Camera / video
# ---------------------------------------------------------------------------
DEFAULT_CAMERA_INDEX = 0     # 0 = default laptop webcam
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# ---------------------------------------------------------------------------
# GPS simulation
# ---------------------------------------------------------------------------
# A pleasant starting point (Bengaluru, India). The simulator "drives" the
# vehicle from here. Change to your own city for a localized demo.
START_LAT = 12.9716
START_LON = 77.5946

# How far the simulated vehicle moves each tick (roughly). ~0.00003 deg ≈ 3 m.
GPS_STEP = 0.00003
GPS_JITTER = 0.000008  # small randomness so the path is not a straight line

# ---------------------------------------------------------------------------
# Road memory / deduplication
# ---------------------------------------------------------------------------
# If a new hazard of the same type is within this many metres of an existing
# stored hazard, we treat it as a duplicate and do NOT insert a new row.
DEDUP_DISTANCE_M = 15.0

# ---------------------------------------------------------------------------
# Driver alert system
# ---------------------------------------------------------------------------
# Warn the driver when the vehicle comes within this many metres of a stored
# hazard.
ALERT_DISTANCE_M = 30.0

# Do not re-alert for the same hazard until the vehicle has moved away and
# this cooldown (seconds) has elapsed.
ALERT_COOLDOWN_S = 20.0

VOICE_ALERT_TEXT = "Warning. Pothole ahead."

# ---------------------------------------------------------------------------
# Severity estimation (bonus feature)
# ---------------------------------------------------------------------------
# Bounding-box area (as a fraction of the frame area) thresholds mapping to a
# human-readable severity label.
SEVERITY_THRESHOLDS = {
    "Low": 0.02,     # < 2% of frame
    "Medium": 0.06,  # 2% - 6%
    "High": 1.00,    # > 6%
}

# ---------------------------------------------------------------------------
# Map defaults
# ---------------------------------------------------------------------------
MAP_ZOOM_START = 16
MAP_HTML_PATH = DASHBOARD_DIR / "hazard_map.html"

# ---------------------------------------------------------------------------
# CSV export (bonus feature)
# ---------------------------------------------------------------------------
CSV_EXPORT_PATH = DASHBOARD_DIR / "hazard_history.csv"

# ===========================================================================
# FUTURE / OPTIONAL: Cloud synchronization
# ---------------------------------------------------------------------------
# This project is intentionally OFFLINE-FIRST and EDGE-AI: all inference and
# storage happen locally on the laptop. No video frame ever leaves the device.
# A future version could optionally push the SQLite `road_memory` table to a
# cloud endpoint for fleet-wide hazard sharing, e.g.:
#     CLOUD_SYNC_ENABLED = False
#     CLOUD_SYNC_URL = "https://api.example.com/roadsense/sync"
# Left as a comment on purpose — no network calls are made anywhere.
# ===========================================================================
