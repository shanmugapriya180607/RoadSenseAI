"""
gps_simulator.py
================
Simulated GPS for RoadSense AI.

No GPS hardware is available on a laptop, so this module fakes a moving
vehicle. Each call to `update()` nudges the latitude/longitude forward along a
gently curving path (with a little random jitter) so the dashboard shows the
"car" driving. Detected hazards borrow the vehicle's current position.
"""

import math
import random

import config


class GPSSimulator:
    """Simulates a vehicle driving along a road, one step at a time."""

    def __init__(self, start_lat: float = config.START_LAT,
                 start_lon: float = config.START_LON,
                 step: float = config.GPS_STEP,
                 jitter: float = config.GPS_JITTER):
        """
        Initialise the simulated vehicle at a starting coordinate.

        `step`   controls how far the car moves per tick (~metres).
        `jitter` adds small randomness so the path is not perfectly straight.
        """
        self.lat = float(start_lat)
        self.lon = float(start_lon)
        self.step = step
        self.jitter = jitter
        # Heading in radians; slowly rotates so the vehicle appears to turn.
        self._heading = 0.0
        self._ticks = 0

    def update(self) -> tuple[float, float]:
        """
        Advance the vehicle one step and return the new (lat, lon).

        The heading drifts slowly which produces a natural curving route
        instead of a dead-straight line.
        """
        self._ticks += 1

        # Gradually turn the wheel — a slow sinusoidal drift in heading.
        self._heading += 0.15 * math.sin(self._ticks / 8.0)

        # Move along the current heading. Latitude ~ cos(heading), lon ~ sin.
        self.lat += self.step * math.cos(self._heading)
        self.lon += self.step * math.sin(self._heading)

        # Add a touch of randomness so consecutive points are not identical.
        self.lat += random.uniform(-self.jitter, self.jitter)
        self.lon += random.uniform(-self.jitter, self.jitter)

        return self.lat, self.lon

    def current(self) -> tuple[float, float]:
        """Return the vehicle's current position without moving it."""
        return self.lat, self.lon

    def reset(self, lat: float = config.START_LAT, lon: float = config.START_LON) -> None:
        """Teleport the vehicle back to a starting coordinate."""
        self.lat = float(lat)
        self.lon = float(lon)
        self._heading = 0.0
        self._ticks = 0


if __name__ == "__main__":
    # Quick demo: print 10 simulated positions.
    sim = GPSSimulator()
    for i in range(10):
        lat, lon = sim.update()
        print(f"tick {i:02d}:  {lat:.6f}, {lon:.6f}")
