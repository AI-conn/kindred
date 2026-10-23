from kindred.taste import PERSONAS, build_profile
from kindred.compare import baseline_plan, compare
from kindred.narrate import Narrator


def _narrator():
    return Narrator("", "gemini-2.5-flash")


def test_baseline_used_qloo_false(client):
    profile = build_profile(client, PERSONAS[0]["seeds"])
    baseline = baseline_plan(profile["seeds"], _narrator())
    assert baseline["used_qloo_data"] is False


def test_baseline_no_affinity_and_no_tag_names(client):
    profile = build_profile(client, PERSONAS[0]["seeds"])
    baseline = baseline_plan(profile["seeds"], _narrator())
    text = " ".join([baseline.get("note", "")] + [s.get("name", "") + " " + s.get("why", "") for s in baseline["slots"]]).lower()
    assert "affinity" not in text
    for t in profile["tags"]:
        assert t["name"].lower() not in text, f"baseline leaked tag name {t['name']}"


def test_delta_evidence_count(client):
    profile = build_profile(client, PERSONAS[0]["seeds"])
    result = compare(client, profile, _narrator())
    assert result["delta"]["evidence_backed_picks"]["without_qloo"] == 0
    assert result["delta"]["evidence_backed_picks"]["with_qloo"] >= 3
    assert result["delta"]["domains_covered"] == 4
    assert result["delta"]["taste_tags_used"] == len(profile["tags"])
