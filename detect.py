"""
detect.py
=========
Edge-AI hazard detector for RoadSense AI.

Wraps Ultralytics YOLOv8 so the rest of the app can call a single
`detect(frame)` method and get back clean, annotated results. Everything runs
LOCALLY on the laptop CPU/GPU — no frame is ever sent to the cloud.

Key behaviours:
  * Loads a custom-trained model if present (config.CUSTOM_MODEL_PATH),
    otherwise falls back to a pretrained YOLOv8n model so the demo still runs.
  * Maps fallback (COCO) classes to pseudo road-hazard labels so the pipeline
    visibly detects "hazards" even without a custom model.
  * Estimates severity from bounding-box area (bonus feature).
  * Draws bounding boxes, class names and confidence onto frames.
"""

from pathlib import Path

import cv2
import numpy as np

import config

# Ultralytics is imported lazily inside the class so that importing this module
# (e.g. for the DB-only parts of the dashboard) never fails if the heavy ML
# dependency is missing or slow to load.


class HazardDetector:
    """YOLOv8-based detector for potholes, cracks and speed breakers."""

    def __init__(self, model_path: Path | None = None,
                 confidence: float = config.CONFIDENCE_THRESHOLD):
        """
        Load the detection model, preferring a custom-trained file and falling
        back to a pretrained YOLOv8n model.

        Raises no exception on a missing custom model — it downgrades to the
        fallback and records that in `self.using_fallback`.
        """
        self.confidence = confidence
        self.model = None
        self.model_name = None
        self.using_fallback = False
        self._load_model(model_path)

    # ------------------------------------------------------------------ #
    # Model loading (graceful about missing files)
    # ------------------------------------------------------------------ #
    def _load_model(self, model_path: Path | None) -> None:
        """
        Try the custom model first, then the pretrained fallback.

        We import ultralytics here so a slow/failed ML import is contained and
        reported clearly instead of crashing the whole app at import time.
        """
        try:
            from ultralytics import YOLO
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Ultralytics is not installed. Run: pip install ultralytics"
            ) from exc

        candidate = Path(model_path) if model_path else config.CUSTOM_MODEL_PATH

        if candidate.exists():
            # Custom-trained road hazard model available — use it.
            self.model = YOLO(str(candidate))
            self.model_name = candidate.name
            self.using_fallback = False
        else:
            # Fall back to pretrained YOLOv8n. Ultralytics will auto-download
            # the weights on first use if they are not already cached; if a
            # copy exists in models/ we prefer that (fully offline).
            local_fallback = config.MODELS_DIR / config.FALLBACK_MODEL
            weights = str(local_fallback) if local_fallback.exists() else config.FALLBACK_MODEL
            self.model = YOLO(weights)
            self.model_name = config.FALLBACK_MODEL
            self.using_fallback = True

    # ------------------------------------------------------------------ #
    # Severity (bonus): derive from bounding-box size
    # ------------------------------------------------------------------ #
    @staticmethod
    def _severity(box_area: float, frame_area: float) -> str:
        """
        Map the fraction of the frame occupied by the box to a severity label.
        A bigger pothole in view is (roughly) closer/larger => more severe.
        """
        if frame_area <= 0:
            return "Low"
        frac = box_area / frame_area
        for label, threshold in config.SEVERITY_THRESHOLDS.items():
            if frac < threshold:
                return label
        return "High"

    # ------------------------------------------------------------------ #
    # Class-name normalisation
    # ------------------------------------------------------------------ #
    def _normalise_label(self, raw_label: str) -> str | None:
        """
        Convert a raw model label into one of our hazard classes.

        * Custom model: labels already match HAZARD_CLASSES -> return as-is.
        * Fallback model: translate a handful of COCO classes into pseudo
          hazards via config.FALLBACK_HAZARD_MAP; ignore everything else.
        """
        if not self.using_fallback:
            # Trust the custom model's labels (normalise separators).
            return raw_label.strip().lower().replace(" ", "_")

        return config.FALLBACK_HAZARD_MAP.get(raw_label.strip().lower())

    # ------------------------------------------------------------------ #
    # Detection
    # ------------------------------------------------------------------ #
    def detect(self, frame: np.ndarray) -> list[dict]:
        """
        Run inference on a single BGR frame (as read by OpenCV).

        Returns a list of detection dicts:
            {
              "hazard_type": str,
              "confidence":  float,
              "box":         (x1, y1, x2, y2),
              "severity":    str,
            }
        Only hazards above the confidence threshold and recognised by
        `_normalise_label` are returned.
        """
        if frame is None or self.model is None:
            return []

        h, w = frame.shape[:2]
        frame_area = float(h * w)
        results = self.model.predict(frame, conf=self.confidence, verbose=False)

        detections: list[dict] = []
        for res in results:
            names = res.names  # id -> label mapping for this model
            if res.boxes is None:
                continue
            for box in res.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                raw_label = names.get(cls_id, str(cls_id))

                hazard_type = self._normalise_label(raw_label)
                if hazard_type is None:
                    continue  # not a hazard class we care about

                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                box_area = float(abs(x2 - x1) * abs(y2 - y1))
                severity = self._severity(box_area, frame_area)

                detections.append({
                    "hazard_type": hazard_type,
                    "confidence": round(conf, 3),
                    "box": (x1, y1, x2, y2),
                    "severity": severity,
                })

        return detections

    # ------------------------------------------------------------------ #
    # Drawing
    # ------------------------------------------------------------------ #
    @staticmethod
    def draw(frame: np.ndarray, detections: list[dict]) -> np.ndarray:
        """
        Draw bounding boxes, class names, confidence and severity on a copy of
        the frame. Colour is keyed by severity for quick visual triage.
        """
        annotated = frame.copy()
        colours = {
            "Low": (0, 200, 0),      # green
            "Medium": (0, 165, 255),  # orange
            "High": (0, 0, 255),      # red
        }
        for det in detections:
            x1, y1, x2, y2 = det["box"]
            colour = colours.get(det["severity"], (0, 200, 0))
            label = (f'{det["hazard_type"].replace("_", " ")} '
                     f'{det["confidence"] * 100:.0f}% ({det["severity"]})')

            cv2.rectangle(annotated, (x1, y1), (x2, y2), colour, 2)
            # Label background for readability.
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), colour, -1)
            cv2.putText(annotated, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
                        cv2.LINE_AA)
        return annotated


if __name__ == "__main__":
    # Smoke test: build the detector and report which model got loaded.
    det = HazardDetector()
    print(f"Loaded model: {det.model_name}  (fallback={det.using_fallback})")
    # Run on a black test frame just to confirm the pipeline executes.
    blank = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
    print(f"Detections on blank frame: {len(det.detect(blank))}")
