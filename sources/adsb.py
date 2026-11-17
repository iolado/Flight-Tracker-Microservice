# this file makes API calls to adsb.lol to get aircraft data
# https://github.com/adsblol

import requests

BASE_URL = "https://api.adsb.lol"
TIMEOUT_SECONDS = 5


### AIRCRAFT API REQUESTS ###

def aircraft_near(lat, lon, radius):
    """
    Get Aircraft Near a given location
    """
    url = f"{BASE_URL}/v2/point/{lat}/{lon}/{int(radius)}" # adsb rejects floats

    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status() #Raises an exception for bad status codes
    data = response.json()
    # ac is a list, so we need to normalize it
    aircraft_list = data.get("ac", []) 
    return [normalize_response(aircraft) for aircraft in aircraft_list]

def aircraft_by_callsign(callsign):
    """
    Gets aircraft by callsigh
    """
    callsign = callsign.strip().upper()
    url = f"{BASE_URL}/v2/callsign/{callsign}"

    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    # ac is a list, so we need to normalize it
    aircraft = data.get("ac", []) 
    return normalize_response(aircraft[0]) if aircraft else None

    
### DATA ###

def normalize_response(response):
    """
    Normalizes the response from the API
    """
    # Clean up: callsign may be missing or space-padded
    callsign = (response.get("flight") or "").strip() or None

    # Convert: alt_baro is a number OR the string "ground"
    altitude = response.get("alt_baro")
    on_ground = altitude == "ground"
    altitude_ft = None if on_ground else altitude

    return {
        "callsign": callsign,
        "altitude_ft": altitude_ft,
        "on_ground": on_ground,
        "latitude": response.get("lat"),
        "longitude": response.get("lon"),
        "speed_kts": response.get("gs"),
        "heading": response.get("track"),
        "vertical_speed": response.get("baro_rate"),
        "aircraft_type": response.get("t"),
        "distance_nm": response.get("dst"),
    }