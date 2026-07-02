"""
utils/video_source.py
======================
Robust video-frame source for RoadSense AI.

A thin wrapper around cv2.VideoCapture that:
  * opens either a webcam index or a video file path,
  * handles camera-open failures gracefully (never throws on a bad device),
  * loops a video file so demos run continuously,
  * exposes a simple read()/release() interface used by detect + dashboard.
"""

from pathlib import Path

import cv2

import config


class VideoSource:
    """Unified webcam / video-file frame source with graceful failure."""

    def __init__(self, source=config.DEFAULT_CAMERA_INDEX,
                 width: int = config.FRAME_WIDTH,
                 height: int = config.FRAME_HEIGHT,
                 loop: bool = True):
        """
        Args:
            source: webcam index (int) or path to a video file (str/Path).
            width/height: requested capture resolution (best-effort).
            loop:   if True and source is a file, restart when it ends.
        """
        self.source = source
        self.width = width
        self.height = height
        self.loop = loop
        self.is_file = isinstance(source, (str, Path)) and Path(str(source)).exists()
        self.cap = None
        self.error = None
        self._open()

    def _open(self) -> None:
        """
        Open the capture device. On Windows, CAP_DSHOW makes webcams start
        faster and more reliably. Failure is recorded in self.error rather
        than raised, so callers can show a friendly message.
        """
        try:
            if self.is_file:
                self.cap = cv2.VideoCapture(str(self.source))
            else:
                # CAP_DSHOW = DirectShow backend, best for Windows webcams.
                self.cap = cv2.VideoCapture(int(self.source), cv2.CAP_DSHOW)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            if not self.cap or not self.cap.isOpened():
                self.error = (
                    f"Could not open video source '{self.source}'. "
                    "Check that a webcam is connected / not in use, or that "
                    "the video path is valid."
                )
        except Exception as exc:
            self.error = f"Video source error: {exc}"
            self.cap = None

    def is_opened(self) -> bool:
        """Return True if the source is ready to deliver frames."""
        return self.cap is not None and self.cap.isOpened() and self.error is None

    def read(self):
        """
        Read the next frame.

        Returns (ok, frame). For a looping video file, automatically rewinds
        to the first frame when the end is reached so the demo never stops.
        """
        if not self.is_opened():
            return False, None

        ok, frame = self.cap.read()
        if not ok and self.is_file and self.loop:
            # End of file: rewind and try once more.
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
        return ok, frame

    def release(self) -> None:
        """Release the underlying capture device."""
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        self.cap = None
