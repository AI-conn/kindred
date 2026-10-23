import pytest
from kindred.qloo_client import QlooClient, FixtureTransport


def test_search_resolves_amelie(client):
    results = client.search("Amélie")
    assert results
    assert any(r["name"] == "Amélie" for r in results)


def test_search_unknown_returns_empty(client):
    results = client.search("Zqxwv Nonexistent Thing 12345")
    assert results == []


def test_insights_drops_invalid_param(client, transport):
    # filter.price_level.max is invalid for movie
    results = client.insights("urn:entity:movie", entity_ids=[], tag_ids=[], extra={"filter.price_level.max": 2}, take=3)
    # check transport calls for insights
    insight_calls = [(p, params) for p, params in transport.calls if p == "/v2/insights"]
    assert insight_calls
    last_params = insight_calls[-1][1]
    assert "filter.price_level.max" not in last_params
    assert "filter.price_level.max" in client.last_dropped_params


def test_invalid_filter_type_raises(client):
    with pytest.raises(ValueError):
        client.insights("urn:entity:invalid_type_xyz", take=3)
    with pytest.raises(ValueError):
        client.insights("movie", take=3)


def test_insights_excludes_signal_entities(client):
    # search for Grand Budapest
    found = client.search("The Grand Budapest Hotel")
    assert found
    gid = found[0]["id"]
    results = client.insights("urn:entity:movie", entity_ids=[gid], take=10)
    ids = [r["id"] for r in results]
    assert gid not in ids
