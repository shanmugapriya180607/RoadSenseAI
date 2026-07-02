"""
app.py
======
Entry-point launcher for RoadSense AI.

Two convenient ways to run the project:

  1) Recommended (full dashboard UI):
         streamlit run dashboard.py

  2) This launcher, which simply shells out to Streamlit for you:
         python app.py            -> launches the dashboard
         python app.py --headless -> runs a quick console detection demo
                                      (webcam + DB, no Streamlit) for testing

Keeping a plain-python entry point makes the project easy to start for users
who are new to Streamlit, and gives a hardware-free smoke test path.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import config

DASHBOARD = Path(__file__).resolve().parent / "dashboard.py"


def launch_dashboard() -> int:
    """Launch the Streamlit dashboard as a subprocess (portable, no paths)."""
    print("Launching RoadSense AI dashboard…")
    print("If your browser does not open automatically, visit the URL shown "
          "below.\n")
    # `python -m streamlit run` works regardless of PATH quirks on Windows.
    cmd = [sys.executable, "-m", "streamlit", "run", str(DASHBOARD)]
    return subprocess.call(cmd)


def headless_demo(seconds: int = 15) -> None:
    """
    Run a minimal, hardware-free console demo:
      * open the webcam (or fail gracefully),
      * detect hazards,
      * move the simulated GPS,
      * store hazards + fire proximity alerts,
    for a few seconds. Useful to verify the pipeline without the UI.
    """
    import cv2  # local import so the launcher stays lightweight

    from detect import HazardDetector
    from database import RoadMemoryDB, seed_sample_data
    from gps_simulator import GPSSimulator
    from alert import AlertSystem
    from utils.video_source import VideoSource

    print("Headless demo — loading model…")
    detector = HazardDetector()
    print(f"Model: {detector.model_name} (fallback={detector.using_fallback})")

    db = RoadMemoryDB()
    seed_sample_data(db)
    gps = GPSSimulator()
    alerts = AlertSystem(voice=True)

    video = VideoSource(config.DEFAULT_CAMERA_INDEX)
    if video.error:
        print("Camera unavailable:", video.error)
        print("Continuing with GPS + alert simulation only (no video).")

    start = time.time()
    while time.time() - start < seconds:
        lat, lon = gps.update()

        if video.is_opened():
            ok, frame = video.read()
            if ok and frame is not None:
                dets = detector.detect(frame)
                for d in dets:
                    new_id = db.add_hazard(lat, lon, d["hazard_type"], d["confidence"])
                    if new_id:
                        print(f"  + stored {d['hazard_type']} "
                              f"({d['confidence']:.2f}) @ {lat:.5f},{lon:.5f}")

        for ev in alerts.check(lat, lon, db.get_hazards_as_dicts()):
            print("  !!", ev["message"])

        time.sleep(1.0)  # simulate one update per second

    video.release()
    print(f"\nDone. Total hazards in road memory: {db.count()}")
    db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="RoadSense AI launcher")
    parser.add_argument("--headless", action="store_true",
                        help="Run a console detection demo instead of the UI.")
    parser.add_argument("--seconds", type=int, default=15,
                        help="Duration for the headless demo.")
    args = parser.parse_args()

    if args.headless:
        headless_demo(args.seconds)
        return 0
    return launch_dashboard()


if __name__ == "__main__":
    raise SystemExit(main())
