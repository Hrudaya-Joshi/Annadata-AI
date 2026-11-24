import math
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger(__name__)


def calculate_distance_km(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two geographical coordinates.
    Returns distance in kilometres.
    """
    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)

    # Validate coordinates
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
        raise ValueError("Invalid latitude")

    if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError("Invalid longitude")

    earth_radius = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return round(earth_radius * c, 2)


# Local fallback database of known common locations in Bangalore & metros
FALLBACK_LOCATIONS = {
    "indiranagar": (12.9784, 77.6408, "100-Ft Road, Indiranagar, Bengaluru, Karnataka"),
    "koramangala": (12.9345, 77.6265, "80-Ft Road, Koramangala, Bengaluru, Karnataka"),
    "whitefield": (12.9698, 77.7500, "ITPL Main Road, Whitefield, Bengaluru, Karnataka"),
    "bellandur": (12.9260, 77.6834, "Outer Ring Road, Bellandur, Bengaluru, Karnataka"),
    "jayanagar": (12.9308, 77.5838, "4th Block, Jayanagar, Bengaluru, Karnataka"),
    "malleshwaram": (13.0031, 77.5694, "Sampige Road, Malleshwaram, Bengaluru, Karnataka"),
    "yeshwanthpur": (13.0234, 77.5489, "APMC Yard, Yeshwanthpur, Bengaluru, Karnataka"),
    "hebbal": (13.0358, 77.5970, "Bellary Road, Hebbal, Bengaluru, Karnataka"),
    "rajajinagar": (12.9915, 77.5523, "Dr Rajkumar Road, Rajajinagar, Bengaluru, Karnataka"),
    "mg road": (12.9756, 77.6066, "MG Road, Central Business District, Bengaluru, Karnataka"),
    "marathahalli": (12.9591, 77.6974, "Marathahalli Bridge, Bengaluru, Karnataka"),
    "electronic city": (12.8452, 77.6602, "Phase 1, Electronic City, Bengaluru, Karnataka"),
    "austin town": (12.9611, 77.6189, "Austin Town, Neelasandra, Bengaluru, Karnataka"),
    "halasuru": (12.9780, 77.6250, "Ulsoor, Bengaluru, Karnataka"),
    "bengaluru": (12.9716, 77.5946, "Bengaluru, Karnataka, India")
}


def reverse_geocode(lat, lon):
    """
    Convert (lat, lon) coordinates to human-readable address.
    Attempts Nominatim OSM first; falls back gracefully if network is unavailable.
    """
    try:
        lat = float(lat)
        lon = float(lon)
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=18&addressdetails=1"
        headers = {"User-Agent": "ANNADATA-AI-FoodRescue/1.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            display_name = data.get("display_name")
            if display_name:
                return display_name
    except Exception as e:
        logger.debug("Online reverse geocode failed (%s), using local fallback resolution.", e)

    # Local proximity lookup
    closest_loc = None
    min_dist = float("inf")
    for key, (fl_lat, fl_lon, addr) in FALLBACK_LOCATIONS.items():
        try:
            d = calculate_distance_km(lat, lon, fl_lat, fl_lon)
            if d < min_dist:
                min_dist = d
                closest_loc = (key, addr)
        except Exception:
            continue

    if closest_loc and min_dist <= 25.0:
        return f"{closest_loc[1]} (approx. {min_dist}km from {closest_loc[0].title()})"
    return f"Detected Location ({lat:.4f}°N, {lon:.4f}°E), Bengaluru Metropolitan Area"


def forward_geocode(address_str):
    """
    Convert text address to (lat, lon) coordinates.
    Attempts Nominatim OSM first; falls back to local city dictionary.
    """
    if not address_str:
        return (12.9716, 77.5946)

    clean_addr = address_str.strip().lower()

    # Direct fallback match first for immediate responsiveness
    for key, (lat, lon, full_addr) in FALLBACK_LOCATIONS.items():
        if key in clean_addr:
            return (lat, lon)

    # Try OSM Nominatim online
    try:
        query = urllib.parse.quote(address_str)
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
        headers = {"User-Agent": "ANNADATA-AI-FoodRescue/1.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and len(data) > 0:
                return (float(data[0]["lat"]), float(data[0]["lon"]))
    except Exception as e:
        logger.debug("Online forward geocode failed (%s), using default coords.", e)

    # Default Bengaluru central coordinates
    return (12.9716, 77.5946)
