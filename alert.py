"""
alert.py
========
Driver alert system for RoadSense AI.

Continuously compares the vehicle's current simulated GPS against every stored
hazard. When the car comes within `ALERT_DISTANCE_M` metres of a hazard, an
alert is raised — a text warning plus a spoken voice line via `pyttsx3`.

To avoid nagging the driver, each hazard has a cooldown: once alerted, it will
not fire again until the cooldown elapses (and, in practice, the car has
usually driven past it by then).

Voice output runs on a background thread so speaking never blocks the video /
dashboard loop, and it degrades gracefully if no TTS engine is available
(e.g. some headless CI machines).
"""

import threading
import time

from geopy.distance import geodesic

import config

# pyttsx3 is optional at runtime — if the platform has no speech engine we
# simply skip the voice and keep the on-screen warnings working.
try:
    import pyttsx3
    _TTS_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    _TTS_AVAILABLE = False


def speak_async(text: str = config.VOICE_ALERT_TEXT) -> None:
    """
    Speak `text` on a daemon thread so audio never blocks the main loop.

    A fresh engine per utterance avoids pyttsx3's known re-entrancy issues on
    Windows SAPI5. Any failure is swallowed so a missing audio device can
    never crash the app.
    """
    if not _TTS_AVAILABLE:
        return

    def _worker():
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception:
            # No audio device / driver — silently ignore, text alert remains.
            pass

    threading.Thread(target=_worker, daemon=True).start()


class AlertSystem:
    """Proximity-based driver warning system with per-hazard cooldowns."""

    def __init__(self, alert_distance_m: float = config.ALERT_DISTANCE_M,
                 cooldown_s: float = config.ALERT_COOLDOWN_S,
                 voice: bool = True):
        """
        Args:
            alert_distance_m: proximity radius that triggers a warning.
            cooldown_s:       minimum seconds between repeat alerts for the
                              same hazard id.
            voice:            whether to play the spoken warning.
        """
        self.alert_distance_m = alert_distance_m
        self.cooldown_s = cooldown_s
        self.voice = voice
        # Maps hazard id -> last alert timestamp (monotonic seconds).
        self._last_alert: dict[int, float] = {}

    def check(self, current_lat: float, current_lon: float,
              hazards: list[dict]) -> list[dict]:
        """
        Compare the current position against all hazards.

        Returns a list of "alert events" for hazards that are within range and
        not currently on cooldown. Each event is a dict with the hazard fields
        plus a computed `distance_m` and a human-readable `message`.
        """
        now = time.monotonic()
        events: list[dict] = []

        for hz in hazards:
            hz_id = hz.get("id")
            dist = geodesic(
                (current_lat, current_lon),
                (hz["latitude"], hz["longitude"]),
            ).meters

            if dist > self.alert_distance_m:
                continue

            # Respect the cooldown so we do not spam the same hazard.
            last = self._last_alert.get(hz_id, 0.0)
            if now - last < self.cooldown_s:
                continue

            self._last_alert[hz_id] = now

            htype = hz.get("hazard_type", "hazard").replace("_", " ")
            message = f"Warning: {htype} ahead in {dist:.0f} m"
            events.append({**hz, "distance_m": round(dist, 1), "message": message})

            # Fire the spoken warning (non-blocking).
            if self.voice:
                speak_async(config.VOICE_ALERT_TEXT)

        return events

    def reset(self) -> None:
        """Forget all cooldowns (e.g. after clearing the database)."""
        self._last_alert.clear()


if __name__ == "__main__":
    # Quick demo: a hazard 10 m away should trigger, one far away should not.
    system = AlertSystem(voice=False)
    hazards = [
        {"id": 1, "latitude": config.START_LAT, "longitude": config.START_LON,
         "hazard_type": "pothole"},
        {"id": 2, "latitude": config.START_LAT + 0.01, "longitude": config.START_LON,
         "hazard_type": "crack"},
    ]
    fired = system.check(config.START_LAT + 0.00005, config.START_LON, hazards)
    for e in fired:
        print(e["message"])
