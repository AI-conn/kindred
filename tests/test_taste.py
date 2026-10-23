from kindred.taste import PERSONAS, build_profile


def test_each_persona_seeds_resolve(client):
    for persona in PERSONAS:
        profile = build_profile(client, persona["seeds"])
        assert profile["unresolved"] == [], f"{persona['id']} unresolved: {profile['unresolved']}"
        assert len(profile["resolved"]) == len(persona["seeds"])


def test_tags_aggregated_non_empty(client):
    profile = build_profile(client, PERSONAS[0]["seeds"])
    assert profile["tags"]
    assert len(profile["tags"]) >= 1
    for t in profile["tags"]:
        assert "id" in t and "name" in t and "weight" in t


def test_nonsense_seed_unresolved(client):
    profile = build_profile(client, ["Zqxwv Nonsense Seed 999"])
    assert "Zqxwv Nonsense Seed 999" in profile["unresolved"]
    assert profile["resolved"] == []
