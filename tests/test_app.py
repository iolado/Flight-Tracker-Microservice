"""Flask route tests; no live external API requests are made."""

import requests
import pytest
import app as service


@pytest.fixture
def client():
    service.app.config.update(TESTING=True)
    return service.app.test_client()


def test_health(client):
    assert client.get("/health").json == {"status": "ok"}


def test_near_success(client, monkeypatch):
    monkeypatch.setattr(service, "aircraft_near", lambda lat, lon, radius: [
        {"callsign": "UAL123", "distance_nm": 3.2}
    ])
    response = client.get("/aircraft/near?lat=45.59&lon=-122.6&radius=25")
    assert response.status_code == 200
    assert response.json["count"] == 1
    assert response.json["aircraft"][0]["callsign"] == "UAL123"


@pytest.mark.parametrize("query", [
    "lon=0&radius=25", "lat=91&lon=0&radius=25",
    "lat=0&lon=-181&radius=25", "lat=0&lon=0&radius=0",
    "lat=0&lon=0&radius=101", "lat=0&lon=0&radius=1.5",
    "lat=nan&lon=0&radius=25", "lat=nope&lon=0&radius=25",
])
def test_near_invalid_input(client, query):
    response = client.get("/aircraft/near?" + query)
    assert response.status_code == 400
    assert set(response.json) == {"error"}


def test_callsign_case_insensitive(client, monkeypatch):
    captured = []
    def fake_lookup(callsign):
        captured.append(callsign)
        return {"callsign": callsign}
    monkeypatch.setattr(service, "aircraft_by_callsign", fake_lookup)
    response = client.get("/aircraft/callsign/ual123")
    assert response.status_code == 200
    assert response.json == {"callsign": "UAL123"}
    assert captured == ["UAL123"]


def test_callsign_not_found(client, monkeypatch):
    monkeypatch.setattr(service, "aircraft_by_callsign", lambda _: None)
    response = client.get("/aircraft/callsign/ZZ999")
    assert response.status_code == 404
    assert response.json == {"error": "Aircraft not found"}


def test_invalid_callsign(client):
    response = client.get("/aircraft/callsign/!")
    assert response.status_code == 400
    assert "error" in response.json


def test_provider_unavailable(client, monkeypatch):
    def failure(*args):
        raise requests.exceptions.Timeout("mocked timeout")
    monkeypatch.setattr(service, "aircraft_near", failure)
    response = client.get("/aircraft/near?lat=45&lon=-122&radius=25")
    assert response.status_code == 502
    assert "error" in response.json


def test_provider_invalid_json(client, monkeypatch):
    def failure(*args):
        raise ValueError("bad data")
    monkeypatch.setattr(service, "aircraft_by_callsign", failure)
    response = client.get("/aircraft/callsign/UAL123")
    assert response.status_code == 502
    assert "error" in response.json


def test_unknown_route_json_error(client):
    response = client.get("/missing")
    assert response.status_code == 404
    assert "error" in response.json


def test_route_mocks_upstream_requests(client, monkeypatch):
    """Integration-style test: mock the adsb.lol HTTP boundary."""
    from unittest.mock import Mock
    from sources import adsb

    external_response = Mock()
    external_response.json.return_value = {
        "ac": [{"flight": " TEST99 ", "alt_baro": "ground", "lat": 45.0}]
    }
    mocked_get = Mock(return_value=external_response)
    monkeypatch.setattr(adsb.requests, "get", mocked_get)

    response = client.get("/aircraft/near?lat=45&lon=-122&radius=25")
    assert response.status_code == 200
    assert response.json["count"] == 1
    assert response.json["aircraft"][0]["on_ground"] is True
    mocked_get.assert_called_once_with(
        "https://api.adsb.lol/v2/point/45.0/-122.0/25", timeout=5
    )
