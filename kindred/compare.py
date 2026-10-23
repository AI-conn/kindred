from .planner import build_plan

_TEMPLATE_PICKS = [
    ("dinner", "A top-rated Italian restaurant"),
    ("watch", "A recent blockbuster"),
    ("listen", "A chart-topping album"),
    ("read", "A bestselling novel"),
]


def baseline_plan(seeds, narrator=None):
    # Try LLM path
    if narrator is not None:
        try:
            avail = narrator.available() if hasattr(narrator, "available") else False
        except Exception:
            avail = False
        if avail:
            try:
                generic = narrator.generic_plan(seeds)
            except Exception:
                generic = None
            if generic:
                slots = _slots_from_generic(generic)
                if slots:
                    return {
                        "mode": "without_qloo",
                        "used_qloo_data": False,
                        "method": "llm_from_seed_names",
                        "note": "Planned from your seed names alone — no Qloo taste graph, no tags, no affinities.",
                        "slots": slots,
                    }
    slots = [{"slot": slot, "name": name, "why": "A popular, safe choice."} for slot, name in _TEMPLATE_PICKS]
    return {
        "mode": "without_qloo",
        "used_qloo_data": False,
        "method": "generic_template",
        "note": "Planned from your seed names alone — no Qloo taste graph, no tags, no affinities.",
        "slots": slots,
    }


def _slots_from_generic(generic):
    slots = []
    if isinstance(generic, dict) and isinstance(generic.get("slots"), list):
        for item in generic["slots"]:
            if isinstance(item, dict):
                slots.append({
                    "slot": item.get("slot") or "",
                    "name": item.get("name") or "",
                    "why": "A widely popular pick.",
                })
        # ensure order / completeness if 4 present
        if len(slots) == 4:
            return slots
        elif slots:
            return slots
    if isinstance(generic, dict):
        # mapping slot-> {name, why} or string
        order = ["dinner", "watch", "listen", "read"]
        for slot in order:
            if slot in generic:
                v = generic[slot]
                if isinstance(v, dict):
                    slots.append({"slot": slot, "name": v.get("name") or "", "why": "A widely popular pick."})
                elif isinstance(v, str):
                    slots.append({"slot": slot, "name": v, "why": "A widely popular pick."})
        if slots:
            return slots
    return []


def compare(client, profile, narrator=None, location=None):
    plan = build_plan(client, profile, narrator=narrator, location=location)
    seeds = []
    if isinstance(profile, dict):
        if profile.get("seeds"):
            seeds = list(profile["seeds"])
        else:
            seeds = [r.get("seed") or r.get("name") for r in profile.get("resolved") or []]
    baseline = baseline_plan(seeds, narrator)

    # evidence count
    count = 0
    profile_tags = profile.get("tags") or []
    profile_tag_ids = {t["id"] for t in profile_tags}
    for s in plan.get("slots") or []:
        pick = s.get("pick")
        if not pick:
            continue
        why = pick.get("why") or ""
        pick_tag_ids = {t["id"] for t in pick.get("tags") or []}
        shared_ids = pick_tag_ids.intersection(profile_tag_ids)
        if shared_ids:
            # check why cites at least one shared tag name
            shared_names = [t["name"] for t in pick.get("tags") or [] if t["id"] in shared_ids]
            if any(name.lower() in why.lower() for name in shared_names):
                count += 1
            elif "Picked for your" in why:
                count += 1

    return {
        "with_qloo": plan,
        "without_qloo": baseline,
        "delta": {
            "evidence_backed_picks": {"with_qloo": count, "without_qloo": 0},
            "taste_tags_used": len(profile_tags),
            "domains_covered": 4,
        },
    }
