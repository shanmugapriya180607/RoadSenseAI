"""
assistant.py
============
RoadSense AI — offline, on-device chat assistant.

This is a lightweight, RULE-BASED analyst that answers questions about the
user's own road-memory data. It is EDGE-AI / offline-first by design: it never
calls any cloud service — it simply reads the local SQLite database and the
current simulated GPS position and responds in natural language.

It changes NO data — it only reads what the rest of the app has stored.

    (Future upgrade, intentionally left as a comment: swap `answer()` for a
     call to a local LLM (e.g. llama.cpp / Ollama) or the Anthropic API to get
     free-form conversational answers. The intent-matching below keeps the demo
     fully offline with zero dependencies.)
"""

from __future__ import annotations

import pandas as pd
from geopy.distance import geodesic

import config

# Suggested starter prompts shown as clickable chips in the UI.
SUGGESTIONS = [
    "How many hazards do I have?",
    "Where is the nearest hazard?",
    "What is the most common hazard?",
    "Summarize my road memory",
]


def _counts(df: pd.DataFrame) -> dict:
    """Return a {hazard_type: count} mapping from the hazards DataFrame."""
    if df.empty:
        return {}
    return df["hazard_type"].value_counts().to_dict()


def _nearest(df: pd.DataFrame, pos: tuple[float, float]) -> tuple[dict | None, float]:
    """Return (nearest hazard row as dict, distance_m) relative to `pos`."""
    if df.empty or pos is None:
        return None, 0.0
    best, best_d = None, float("inf")
    for _, r in df.iterrows():
        d = geodesic(pos, (r["latitude"], r["longitude"])).meters
        if d < best_d:
            best, best_d = r, d
    return (best.to_dict() if best is not None else None), best_d


def _fmt_type(t: str) -> str:
    """Human-friendly hazard label."""
    return str(t).replace("_", " ").title()


def answer(question: str, df: pd.DataFrame,
           pos: tuple[float, float] | None = None) -> str:
    """
    Produce a natural-language answer to `question` using the local data.

    Args:
        question: the user's message.
        df:       all stored hazards (from RoadMemoryDB.get_all_hazards()).
        pos:      current simulated (lat, lon), if available.

    Returns markdown text.
    """
    q = (question or "").lower().strip()
    total = 0 if df.empty else len(df)
    counts = _counts(df)

    # --- greetings / help ---------------------------------------------------
    if any(w in q for w in ["hi", "hello", "hey", "help", "what can you"]):
        return (
            "👋 Hi! I'm your **RoadSense assistant**. I can answer questions "
            "about your local road memory — all offline. Try:\n\n"
            "- *How many potholes have I detected?*\n"
            "- *Where is the nearest hazard?*\n"
            "- *What's the most common hazard?*\n"
            "- *Summarize my road memory*"
        )

    if total == 0:
        return ("Your road memory is currently **empty** — no hazards stored "
                "yet. Head to **Live Detection** and start the camera to begin "
                "building it, and I'll have plenty to tell you about. 🛣️")

    # --- how it works -------------------------------------------------------
    if any(w in q for w in ["how do you work", "how does this work",
                            "how it works", "edge ai", "offline", "privacy",
                            "cloud"]):
        return (
            "RoadSense runs **100% on your laptop**. YOLOv8 detects potholes, "
            "cracks and speed breakers from your camera, each is saved with a "
            "GPS location in a local SQLite database, and you're warned when you "
            "approach one again. **No video ever leaves your device** — and "
            "neither do these answers. 🔒"
        )

    # --- nearest hazard -----------------------------------------------------
    if any(w in q for w in ["near", "close", "closest", "nearby", "ahead"]):
        row, dist = _nearest(df, pos)
        if row is None:
            return "I couldn't determine your position yet, so I can't find the nearest hazard."
        conf = float(row.get("confidence", 0)) * 100
        return (f"🚧 The nearest hazard is a **{_fmt_type(row['hazard_type'])}** "
                f"about **{dist:.0f} m** away "
                f"(detected at {conf:.0f}% confidence).\n\n"
                f"Location: `{row['latitude']:.5f}, {row['longitude']:.5f}`")

    # --- most common --------------------------------------------------------
    if any(w in q for w in ["most common", "most frequent", "mostly",
                            "biggest", "worst"]):
        top = max(counts, key=counts.get)
        return (f"The most common hazard in your road memory is "
                f"**{_fmt_type(top)}** with **{counts[top]}** occurrence(s), "
                f"out of {total} total.")

    # --- confidence ---------------------------------------------------------
    if "confidence" in q or "accurate" in q or "accuracy" in q:
        avg = df["confidence"].mean() * 100
        return (f"Your detections have an **average confidence of "
                f"{avg:.0f}%** across {total} hazards. The model only stores "
                f"detections above {int(config.CONFIDENCE_THRESHOLD * 100)}%.")

    # --- per-type counts (pothole / crack / speed breaker) ------------------
    for key, label in (("pothole", "pothole"), ("crack", "crack"),
                       ("speed", "speed_breaker")):
        if key in q:
            n = counts.get(label, 0)
            share = (n / total * 100) if total else 0
            return (f"You have **{n} {_fmt_type(label)}(s)** stored — "
                    f"that's {share:.0f}% of your {total} recorded hazards.")

    # --- totals / counts ----------------------------------------------------
    if any(w in q for w in ["how many", "count", "total", "number"]):
        parts = ", ".join(f"{v} {_fmt_type(k)}(s)" for k, v in counts.items())
        return f"You have **{total} hazards** in road memory: {parts}."

    # --- summary ------------------------------------------------------------
    if any(w in q for w in ["summar", "overview", "report", "tell me",
                            "status", "recap"]):
        parts = ", ".join(f"{v} {_fmt_type(k)}(s)" for k, v in counts.items())
        avg = df["confidence"].mean() * 100
        row, dist = _nearest(df, pos)
        near = (f" The closest one is a {_fmt_type(row['hazard_type'])} "
                f"~{dist:.0f} m away." if row else "")
        return (f"📋 **Road memory summary**\n\n"
                f"- **{total}** hazards stored: {parts}\n"
                f"- Average confidence: **{avg:.0f}%**\n"
                f"- Most common: **{_fmt_type(max(counts, key=counts.get))}**"
                f"{near}")

    # --- fallback -----------------------------------------------------------
    return (
        "I can help with your road-memory data — counts, the nearest hazard, "
        "the most common type, confidence, or a summary. Try asking "
        "*“summarize my road memory”* or *“where is the nearest hazard?”* 🙂"
    )
