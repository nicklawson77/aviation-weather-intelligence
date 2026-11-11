"""Airport selection policy for the aviation intelligence rebuild.

KDLF is the only active station until its cloud guidance is validated.
CONUS station lookup is a planned feature, not enabled in this version.
"""
INITIAL_STATION = "KDLF"
INITIAL_AIRPORT = {
    "icao": "KDLF",
    "name": "Laughlin Air Force Base",
    "latitude": 29.3594,
    "longitude": -100.7779,
    "elevation_ft": 1082,
}
CONUS_STATION_LOOKUP_ENABLED = False

def active_station(icao=INITIAL_STATION):
    code = str(icao).strip().upper()
    if code != INITIAL_STATION:
        raise ValueError("Only KDLF is enabled during the validation phase.")
    return dict(INITIAL_AIRPORT)
