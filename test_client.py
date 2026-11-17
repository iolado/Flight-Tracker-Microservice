"""Small, independent client program used to demo the flight microservice."""

import json
import requests

BASE = "http://127.0.0.1:5002"


def show(path, params=None):
    try:
        response = requests.get(BASE + path, params=params, timeout=10)
        print(f"\nGET {response.url} -> HTTP {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as exc:
        print(f"Microservice unavailable: {exc}")


if __name__ == "__main__":
    show("/health")
    show("/aircraft/near", {"lat": 45.59, "lon": -122.6, "radius": 25})
    show("/aircraft/callsign/UAL123")
