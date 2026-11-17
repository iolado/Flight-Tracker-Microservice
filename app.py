"""HTTP communication layer for the Flight Tracker microservice."""

import math
import re

import requests
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from sources.adsb import aircraft_by_callsign, aircraft_near

app = Flask(__name__)
MAX_RADIUS_NM = 100  


def error_response(message, status):
    """Return the same JSON error shape across all API routes."""
    return jsonify({"error": message}), status


def numeric_arg(name, minimum, maximum):
    """Parse a required, finite numeric query argument within a range."""
    raw = request.args.get(name)
    if raw is None or not raw.strip():
        raise ValueError(f"{name} is required")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/aircraft/near")
def nearby_aircraft():
    try:
        lat = numeric_arg("lat", -90, 90)
        lon = numeric_arg("lon", -180, 180)
        radius = numeric_arg("radius", 1, MAX_RADIUS_NM)
        # Reject fractions rather than silently truncating e.g. 1.5 to 1.
        if not radius.is_integer():
            return error_response("radius must be a whole number", 400)
    except ValueError as exc:
        return error_response(str(exc), 400)

    try:
        aircraft = aircraft_near(lat, lon, int(radius))
    except requests.exceptions.RequestException:
        return error_response("Flight data provider is unavailable", 502)
    except (ValueError, KeyError, TypeError):
        return error_response("Flight data provider returned invalid data", 502)
    return jsonify({"count": len(aircraft), "aircraft": aircraft})


@app.get("/aircraft/callsign/<callsign>")
def callsign_aircraft(callsign):
    callsign = callsign.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,12}", callsign):
        return error_response("callsign must contain 2-12 letters or digits", 400)
    try:
        aircraft = aircraft_by_callsign(callsign)
    except requests.exceptions.RequestException:
        return error_response("Flight data provider is unavailable", 502)
    except (ValueError, KeyError, TypeError):
        return error_response("Flight data provider returned invalid data", 502)
    if aircraft is None:
        return error_response("Aircraft not found", 404)
    return jsonify(aircraft)


@app.errorhandler(HTTPException)
def handle_http_error(exc):
    return error_response(exc.description, exc.code)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=False)
