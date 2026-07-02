# 🛣️ RoadSense AI: Giving Memory to Vehicles

> An **Edge-AI** road-hazard detection system that spots **potholes, cracks, and
> speed breakers** from a laptop webcam or a road video, **remembers** where it
> saw them (simulated GPS + local database), and **warns the driver** when the
> vehicle approaches a previously detected hazard.

Runs **entirely on a Windows laptop** — no Raspberry Pi, Arduino, Jetson, or any
external hardware required. All AI inference happens **locally**; **no video ever
leaves your device**.

---

## 📖 Project Overview

Roads change faster than maps do. A pothole that appears today is not on any
navigation app tomorrow. **RoadSense AI** gives vehicles a *memory*: as you
drive, an on-device AI model watches the road, records every hazard it detects
together with a (simulated) GPS location in a local SQLite database, and then
proactively warns you the next time you approach that spot — complete with a
spoken *"Warning. Pothole ahead."*

This repository is a **hackathon-ready prototype**: modular, beginner-friendly,
and easy to explain in a live demo.

---

## ✨ Features

- **Premium UI (Light + Dark)** — a startup-grade design system (`ui.py`) with a
  dark "mission-control" aesthetic: near-black background with neon
  violet/cyan/pink accents, glass cards with glow-blobs, gradient-text headings,
  uppercase monospace micro-labels, a subtle grid backdrop, and smooth
  animations (Google Fonts: Inter + Space Grotesk + JetBrains Mono).
  A **theme switch** in the sidebar (and on the auth pages) toggles light/dark
  and the choice is **saved to disk** (`database/app_settings.json`).
- **Official-style App Flow** — a landing **Home** page, a real **Sign In /
  Sign Up** experience, and a **protected dashboard** behind login (just like a
  production app).
- **Secure Local Accounts** — user accounts live in a local SQLite database with
  salted **PBKDF2-HMAC-SHA256** password hashing (no plain-text passwords, no
  cloud, no external auth dependency).
- **Live Camera Detection** — real-time hazard detection from webcam or a local
  road video, with bounding boxes, class names, and confidence scores.
- **Road Memory** — every hazard is saved to SQLite (id, latitude, longitude,
  hazard type, confidence, timestamp) with **duplicate suppression** so the same
  pothole is not stored dozens of times.
- **Simulated GPS** — a virtual vehicle "drives" along a gently curving route,
  updating its position every second (no GPS hardware needed).
- **Driver Alert System** — when the vehicle comes within ~30 m of a remembered
  hazard, a **visual popup** and an **offline voice alert** fire, with a cooldown
  to prevent repeated warnings.
- **Interactive Dashboard** (Streamlit) — live feed, statistics, history table,
  Folium map, current position, and a live alerts panel.
- **Edge-AI by design** — 100% local inference, **offline-first**, no cloud.

### 🎁 Bonus features included
- Severity estimation from bounding-box size (Low / Medium / High, colour-coded).
- Export hazard history to **CSV**.
- **Dark-mode-friendly** UI styling.
- **Charts** (hazards by type).
- **Search** hazards by type and **filter by date**.
- Sample seed data so the dashboard looks alive on first launch.

---

## 🧰 Tech Stack

| Area            | Technology                                   |
|-----------------|----------------------------------------------|
| Language        | Python 3.11+                                  |
| AI Model        | Ultralytics **YOLOv8 Nano** (custom or pretrained fallback) |
| Vision          | OpenCV, NumPy                                 |
| Dashboard       | Streamlit                                     |
| Data            | SQLite3, Pandas                              |
| Map             | Folium                                        |
| Voice / Geo     | pyttsx3, geopy                                |

---

## 📁 Folder Structure

```
RoadSenseAI/
├── dataset/            # (place your training images / demo road videos here)
├── models/            # YOLO weights (.pt) — custom or pretrained
├── database/          # SQLite files (road_memory.db + users.db) auto-created
├── dashboard/         # generated assets (map HTML, CSV exports)
├── utils/
│   ├── __init__.py
│   └── video_source.py    # robust webcam / video-file frame source
├── config.py          # all paths, thresholds & tunables (no hardcoded paths)
├── auth.py            # user accounts + Home / Login / Sign Up pages
├── database.py        # SQLite "road memory" layer (OOP)
├── gps_simulator.py   # simulated moving-vehicle GPS
├── detect.py          # YOLOv8 hazard detector + drawing + severity
├── alert.py           # proximity voice/visual alert system
├── map_utils.py       # Folium interactive hazard map builder
├── dashboard.py       # ⭐ app entry: Home → Sign In → Dashboard (run this)
├── app.py             # launcher (starts dashboard, or a headless demo)
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

> Prerequisite: **Python 3.11 or newer** installed and on your PATH.

```powershell
# 1. Clone or copy this project, then open it in a terminal
cd RoadSenseAI

# 2. (Recommended) create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

The first run will auto-download the pretrained **YOLOv8n** weights (~6 MB) if
you do not supply a custom model — this is the only time the network is used.

### Using a custom-trained model (optional)
Drop your trained weights at:

```
models/roadsense_yolov8n.pt
```

with classes named `pothole`, `crack`, `speed_breaker`. RoadSense AI will detect
and use it automatically. If it is absent, the app **gracefully falls back** to a
pretrained model so the demo still runs (mapping a few generic classes to
"hazards" for illustration).

---

## ▶️ How to Run

**Option A — full dashboard (recommended):**
```powershell
streamlit run dashboard.py
```
…or simply:
```powershell
python app.py
```

**Option B — hardware-free console smoke test (no UI):**
```powershell
python app.py --headless --seconds 15
```

Each module is also runnable on its own for quick testing, e.g.:
```powershell
python database.py       # creates DB + seeds sample data
python gps_simulator.py  # prints simulated GPS track
python detect.py         # loads the model + runs on a blank frame
python map_utils.py      # writes a demo map to dashboard/hazard_map.html
```

---

## 🔑 Signing In

The app opens on a **Home** page. Click **Sign In** and use the seeded demo
account (shown right on the login screen):

| Username | Password   |
|----------|------------|
| `admin`  | `admin123` |

…or click **Sign Up** to create your own account. Accounts are stored locally in
`database/users.db` with hashed passwords. After signing in you land on the
protected dashboard; **Log out** is in the sidebar.

---

## 🎬 Demo Instructions (for judges / presentation)

1. Run `streamlit run dashboard.py`. You land on the **Home** page.
2. Click **Sign In** and log in with `admin` / `admin123` (or sign up). The
   **dashboard** opens with **sample hazards** already on the map (seeded so it
   looks alive).
4. In the sidebar, click **▶ Start Camera** (or paste a road video path and click
   **🎬 Load Video**). Live detection begins in the left panel.
5. As hazards are detected, watch the **Total Hazards** metric and the **history
   table** grow; new markers appear on the **map**.
6. The **simulated vehicle** (green car marker) moves every second. When it
   drives within ~30 m of a stored hazard, an **alert** appears in the Alerts
   panel and you hear *"Warning. Pothole ahead."*
7. Show **filters** (by type / date), the **chart**, and **Export CSV** to
   demonstrate the road-memory data.
8. Click **🗑 Clear Database** to reset for the next run.

> Tip: for a repeatable demo with no webcam, put a short road clip in
> `dataset/` and use **Load Video** — it loops automatically.

---

## 🚀 Future Enhancements

- Real GPS integration (USB/Bluetooth NMEA receiver or phone GPS).
- Cloud sync of the road-memory table for **fleet-wide** hazard sharing
  (see the commented stub in `config.py` — currently **disabled by design**).
- Automatic hazard severity → maintenance-priority reporting for city councils.
- On-device model quantization for even faster edge inference.
- Multi-vehicle crowd-sourced mapping and confidence weighting.
- Mobile companion app with turn-by-turn hazard warnings.

---

## 🖼️ Screenshots

> _Placeholders — capture these during your demo and drop the images in
> `dashboard/` or `docs/`._

| Live Detection | Interactive Map |
|----------------|-----------------|
| ![Live detection placeholder](docs/screenshot_live.png) | ![Map placeholder](docs/screenshot_map.png) |

| Statistics & History | Alerts Panel |
|----------------------|--------------|
| ![Stats placeholder](docs/screenshot_stats.png) | ![Alerts placeholder](docs/screenshot_alerts.png) |

---

## 🔒 Privacy & Edge-AI Statement

RoadSense AI is **offline-first**. Video frames are processed **on the laptop**
and are **never uploaded** anywhere. The only optional network activity is the
one-time download of pretrained model weights when no custom model is provided.

---

## 📝 License

Released as a hackathon prototype for educational and demonstration purposes.
