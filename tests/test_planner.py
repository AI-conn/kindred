from kindred.taste import PERSONAS, build_profile
from kindred.planner import build_plan
from kindred.narrate import Narrator


def _narrator():
    return Narrator("", "gemini-2.5-flash")


def test_plan_has_4_slots_and_picks(client):
    profile = build_profile(client, PERSONAS[0]["seeds"])
    plan = build_plan(client, profile, narrator=_narrator())
    assert len(plan["slots"]) == 4
    for slot in plan["slots"]:
        assert slot["pick"] is not None, f"slot {slot['slot']} pick is null"
        assert slot["pick"]["why"]
    # every why non-empty already checked; dinner why names a shared tag
    dinner = [s for s in plan["slots"] if s["slot"] == "dinner"][0]
    why = dinner["pick"]["why"]
    assert why
    # shared tag names from profile
    profile_tag_names = [t["name"] for t in profile["tags"]]
    pick_tag_names = [t["name"] for t in dinner["pick"]["tags"]]
    shared = [n for n in pick_tag_names if n in profile_tag_names]
    assert shared, "dinner pick should share a tag with profile"
    assert any(name.lower() in why.lower() for name in shared), f"dinner why '{why}' should name a shared tag {shared}"


def test_half_the_budget_only_place(client, transport):
    profile = build_profile(client, PERSONAS[0]["seeds"])
    transport.calls.clear()
    plan = build_plan(client, profile, narrator=_narrator(), refinements=["half-the-budget"])
    insight_calls = [(p, params) for p, params in transport.calls if p == "/v2/insights"]
    assert insight_calls
    for path, params in insight_calls:
        if params.get("filter.type") == "urn:entity:place":
            assert params.get("filter.price_level.max") == 2
        else:
            assert "filter.price_level.max" not in params
    assert "half-the-budget" in plan["meta"]["refinements_applied"]


def test_quieter_all_slots(client, transport):
    profile = build_profile(client, PERSONAS[0]["seeds"])
    transport.calls.clear()
    plan = build_plan(client, profile, narrator=_narrator(), refinements=["quieter"])
    insight_calls = [(p, params) for p, params in transport.calls if p == "/v2/insights"]
    assert len(insight_calls) == 4
    for path, params in insight_calls:
        assert params.get("filter.popularity.max") == 0.85
    assert "quieter" in plan["meta"]["refinements_applied"]


def test_closer_to_home_without_location_ignored(client):
    profile = build_profile(client, PERSONAS[0]["seeds"])
    plan = build_plan(client, profile, narrator=_narrator(), refinements=["closer-to-home"])
    assert "closer-to-home" in plan["meta"]["refinements_ignored"]
    # note exists mentioning it (in notes)
    notes_text = " ".join(plan["meta"]["notes"]).lower()
    assert "closer" in notes_text or "location" in notes_text


def test_unknown_refinement_ignored(client):
    profile = build_profile(client, PERSONAS[0]["seeds"])
    plan = build_plan(client, profile, narrator=_narrator(), refinements=["make-it-spicier-xyz"])
    assert "make-it-spicier-xyz" in plan["meta"]["refinements_ignored"]
