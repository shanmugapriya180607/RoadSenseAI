"""
database.py
===========
SQLite persistence layer for RoadSense AI — the "road memory".

This module wraps all database access behind a small class so the rest of the
app never writes raw SQL. The database and table are created automatically on
first use, so the project runs immediately after cloning.

Table: road_memory
    id           INTEGER PRIMARY KEY AUTOINCREMENT
    latitude     REAL
    longitude    REAL
    hazard_type  TEXT
    confidence   REAL
    timestamp    TEXT   (ISO-8601 string)
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from geopy.distance import geodesic

import config


class RoadMemoryDB:
    """Object-oriented wrapper around the SQLite road-memory database."""

    def __init__(self, db_path: Path = config.DB_PATH, table: str = config.DB_TABLE):
        """
        Open (and if needed create) the SQLite database.

        `check_same_thread=False` lets Streamlit's threads share the connection,
        which is safe here because we serialize writes through simple methods.
        """
        self.db_path = Path(db_path)
        self.table = table
        # Make sure the parent folder exists (portable, no hardcoded paths).
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    # ------------------------------------------------------------------ #
    # Schema
    # ------------------------------------------------------------------ #
    def _create_table(self) -> None:
        """Create the road_memory table if it does not already exist."""
        self.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table} (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude    REAL    NOT NULL,
                longitude   REAL    NOT NULL,
                hazard_type TEXT    NOT NULL,
                confidence  REAL    NOT NULL,
                timestamp   TEXT    NOT NULL
            )
            """
        )
        self.conn.commit()

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #
    def is_duplicate(self, latitude: float, longitude: float, hazard_type: str,
                     radius_m: float = config.DEDUP_DISTANCE_M) -> bool:
        """
        Return True if a hazard of the same type already exists within
        `radius_m` metres of the given coordinate.

        This prevents the DB from filling with dozens of rows for the same
        pothole detected across consecutive frames.
        """
        rows = self.conn.execute(
            f"SELECT latitude, longitude FROM {self.table} WHERE hazard_type = ?",
            (hazard_type,),
        ).fetchall()
        for row in rows:
            dist = geodesic((latitude, longitude), (row["latitude"], row["longitude"])).meters
            if dist <= radius_m:
                return True
        return False

    def add_hazard(self, latitude: float, longitude: float, hazard_type: str,
                   confidence: float, dedup: bool = True) -> int | None:
        """
        Insert a hazard into the database.

        If `dedup` is True (default), skip insertion when an equivalent hazard
        already exists nearby and return None. Otherwise return the new row id.
        """
        if dedup and self.is_duplicate(latitude, longitude, hazard_type):
            return None

        timestamp = datetime.now().isoformat(timespec="seconds")
        cur = self.conn.execute(
            f"""INSERT INTO {self.table}
                (latitude, longitude, hazard_type, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?)""",
            (float(latitude), float(longitude), str(hazard_type),
             float(confidence), timestamp),
        )
        self.conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #
    def get_all_hazards(self) -> pd.DataFrame:
        """Return the entire road_memory table as a pandas DataFrame."""
        return pd.read_sql_query(
            f"SELECT * FROM {self.table} ORDER BY id DESC", self.conn
        )

    def get_hazards_as_dicts(self) -> list[dict]:
        """Return all hazards as a list of plain dicts (handy for maps/alerts)."""
        rows = self.conn.execute(
            f"SELECT * FROM {self.table} ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def count(self) -> int:
        """Return the total number of stored hazards."""
        return self.conn.execute(
            f"SELECT COUNT(*) FROM {self.table}"
        ).fetchone()[0]

    def counts_by_type(self) -> dict[str, int]:
        """Return a {hazard_type: count} mapping for the statistics panel."""
        rows = self.conn.execute(
            f"SELECT hazard_type, COUNT(*) AS n FROM {self.table} GROUP BY hazard_type"
        ).fetchall()
        return {r["hazard_type"]: r["n"] for r in rows}

    # ------------------------------------------------------------------ #
    # Maintenance / bonus features
    # ------------------------------------------------------------------ #
    def clear(self) -> None:
        """Delete every row (used by the dashboard 'Clear Database' button)."""
        self.conn.execute(f"DELETE FROM {self.table}")
        self.conn.commit()

    def export_csv(self, csv_path: Path = config.CSV_EXPORT_PATH) -> Path:
        """Export the full history to CSV and return the file path (bonus)."""
        df = self.get_all_hazards()
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False)
        return csv_path

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        try:
            self.conn.close()
        except Exception:
            pass


def seed_sample_data(db: "RoadMemoryDB", n: int = 6) -> None:
    """
    Populate the database with a few deterministic sample hazards so the
    dashboard/map look alive on first launch (useful for a hackathon demo).

    Only seeds when the table is empty so we never overwrite real detections.
    """
    if db.count() > 0:
        return

    # A small spread of hazards around the configured start point.
    samples = [
        (config.START_LAT + 0.00050, config.START_LON + 0.00040, "pothole", 0.91),
        (config.START_LAT + 0.00120, config.START_LON + 0.00010, "crack", 0.77),
        (config.START_LAT + 0.00030, config.START_LON - 0.00070, "speed_breaker", 0.85),
        (config.START_LAT - 0.00060, config.START_LON + 0.00090, "pothole", 0.88),
        (config.START_LAT + 0.00200, config.START_LON + 0.00150, "crack", 0.72),
        (config.START_LAT - 0.00110, config.START_LON - 0.00040, "speed_breaker", 0.80),
    ][:n]

    for lat, lon, htype, conf in samples:
        db.add_hazard(lat, lon, htype, conf, dedup=False)


if __name__ == "__main__":
    # Quick self-test: create DB, seed data, print a summary.
    _db = RoadMemoryDB()
    seed_sample_data(_db)
    print(f"Database at: {_db.db_path}")
    print(f"Total hazards: {_db.count()}")
    print(f"By type: {_db.counts_by_type()}")
    _db.close()
