import os
os.environ["QLOO_TRANSPORT"] = "fixture"

from fastapi.testclient import TestClient
from kindred.main import app
from kindred.taste import PERSONAS

client_http = TestClient(app)


def test_health_transport_fixture():
    r = client_http.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["transport"] == "fixture"


def test_personas_has_3():
    r = client_http.get("/api/personas")
    assert r.status_code == 200
    data = r.json()
    assert len(data["personas"]) == 3


def test_plan_persona_seeds():
    seeds = PERSONAS[0]["seeds"]
    r = client_http.post("/api/plan", json={"seeds": seeds})
    assert r.status_code == 200
    data = r.json()
    assert len(data["slots"]) == 4
    assert "profile" in data
    assert "intro" in data
    assert "meta" in data


def test_plan_empty_seeds_422():
    r = client_http.post("/api/plan", json={"seeds": []})
    assert r.status_code == 422
    assert r.json().get("detail") == "Give me at least one favorite to start from."


def test_compare_shape():
    seeds = PERSONAS[0]["seeds"]
    r = client_http.post("/api/compare", json={"seeds": seeds})
    assert r.status_code == 200
    data = r.json()
    assert "with_qloo" in data
    assert "without_qloo" in data
    assert "delta" in data
    assert data["without_qloo"]["used_qloo_data"] is False
