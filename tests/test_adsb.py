"""Unit tests for ADS-B response normalization and API client."""

from unittest.mock import Mock

from sources import adsb


def test_normalize_airborne_record():
    actual = adsb.normalize_response({
        "flight": " UAL123  ", "alt_baro": 35000, "lat": 45.59,
        "lon": -122.6, "gs": 450.2, "track": 270.5,
        "baro_rate": -64, "t": "B738", "dst": 3.2,
    })
    assert actual["callsign"] == "UAL123"
    assert actual["altitude_ft"] == 35000
    assert actual["on_ground"] is False
    assert actual["distance_nm"] == 3.2


def test_normalize_ground_aircraft():
    actual = adsb.normalize_response({"flight": " TEST1 ", "alt_baro": "ground"})
    assert actual["on_ground"] is True
    assert actual["altitude_ft"] is None


def test_normalize_missing_fields():
    actual = adsb.normalize_response({})
    assert actual["callsign"] is None
    assert actual["latitude"] is None
    assert actual["longitude"] is None
    assert actual["speed_kts"] is None
    assert actual["distance_nm"] is None
    assert actual["on_ground"] is False


def test_callsign_is_uppercased(monkeypatch):
    response = Mock()
    response.json.return_value = {"ac": [{"flight": " UAL123 "}]}
    monkeypatch.setattr(adsb.requests, "get", Mock(return_value=response))
    actual = adsb.aircraft_by_callsign("ual123")
    assert actual["callsign"] == "UAL123"
    adsb.requests.get.assert_called_once_with(
        "https://api.adsb.lol/v2/callsign/UAL123", timeout=5
    )


def test_callsign_returns_first_match(monkeypatch):
    response = Mock()
    response.json.return_value = {"ac": [{"flight": "ONE"}, {"flight": "TWO"}]}
    monkeypatch.setattr(adsb.requests, "get", Mock(return_value=response))
    assert adsb.aircraft_by_callsign("one")["callsign"] == "ONE"
