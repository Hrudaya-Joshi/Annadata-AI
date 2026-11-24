import math


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