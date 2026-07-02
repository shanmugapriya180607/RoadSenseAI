"""
map_utils.py
============
Folium map helpers for RoadSense AI.

Builds an interactive map that plots every stored hazard plus the vehicle's
current position. The dashboard renders the returned map's HTML inline.
"""

import folium
import pandas as pd

import config

# Colour + icon per hazard type so the map is instantly readable.
HAZARD_STYLE = {
    "pothole": ("red", "exclamation-triangle"),
    "crack": ("orange", "road"),
    "speed_breaker": ("blue", "tachometer"),
}


def build_hazard_map(hazards: pd.DataFrame | list[dict],
                     vehicle_pos: tuple[float, float] | None = None,
                     zoom_start: int = config.MAP_ZOOM_START) -> folium.Map:
    """
    Build a Folium map with a marker for every hazard and (optionally) the
    current vehicle position.

    Args:
        hazards:     DataFrame or list-of-dicts with latitude/longitude/
                     hazard_type/confidence columns.
        vehicle_pos: (lat, lon) of the simulated car, drawn as a car marker.
        zoom_start:  initial map zoom level.

    Returns:
        A folium.Map ready to be rendered to HTML.
    """
    # Accept either a DataFrame or a list of dicts.
    if isinstance(hazards, pd.DataFrame):
        records = hazards.to_dict("records")
    else:
        records = list(hazards)

    # Centre the map on the vehicle, else the first hazard, else the config
    # start point — so the map always opens somewhere sensible.
    if vehicle_pos is not None:
        center = list(vehicle_pos)
    elif records:
        center = [records[0]["latitude"], records[0]["longitude"]]
    else:
        center = [config.START_LAT, config.START_LON]

    fmap = folium.Map(location=center, zoom_start=zoom_start, control_scale=True)

    # One marker per stored hazard.
    for r in records:
        htype = str(r.get("hazard_type", "pothole"))
        colour, icon = HAZARD_STYLE.get(htype, ("gray", "info-sign"))
        popup = folium.Popup(
            html=(f"<b>{htype.replace('_', ' ').title()}</b><br>"
                  f"Confidence: {float(r.get('confidence', 0)) * 100:.0f}%<br>"
                  f"Time: {r.get('timestamp', 'n/a')}"),
            max_width=250,
        )
        folium.Marker(
            location=[r["latitude"], r["longitude"]],
            popup=popup,
            tooltip=htype.replace("_", " ").title(),
            icon=folium.Icon(color=colour, icon=icon, prefix="fa"),
        ).add_to(fmap)

        # A faint circle showing the ~30 m alert radius around each hazard.
        folium.Circle(
            location=[r["latitude"], r["longitude"]],
            radius=config.ALERT_DISTANCE_M,
            color=colour,
            weight=1,
            fill=True,
            fill_opacity=0.08,
        ).add_to(fmap)

    # The vehicle marker (green car) on top of everything.
    if vehicle_pos is not None:
        folium.Marker(
            location=list(vehicle_pos),
            tooltip="Your vehicle",
            popup="Current position",
            icon=folium.Icon(color="green", icon="car", prefix="fa"),
        ).add_to(fmap)

    return fmap


def map_to_html(fmap: folium.Map) -> str:
    """Return the map as a self-contained HTML string for embedding."""
    return fmap.get_root().render()


def save_map(fmap: folium.Map, path=config.MAP_HTML_PATH) -> str:
    """Save the map to an HTML file and return the path (for offline viewing)."""
    fmap.save(str(path))
    return str(path)


if __name__ == "__main__":
    # Demo: build a map from a couple of fake hazards and save it.
    demo = [
        {"latitude": config.START_LAT, "longitude": config.START_LON,
         "hazard_type": "pothole", "confidence": 0.9, "timestamp": "now"},
    ]
    m = build_hazard_map(demo, vehicle_pos=(config.START_LAT, config.START_LON))
    print("Saved demo map to:", save_map(m))
