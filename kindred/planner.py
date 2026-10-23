from .narrate import Narrator

SLOTS = [("dinner", "urn:entity:place"), ("watch", "urn:entity:movie"), ("listen", "urn:entity:artist"), ("read", "urn:entity:book")]

_KNOWN_REFINEMENTS = {"quieter", "closer-to-home", "date-night", "half-the-budget"}


def _why_for_pick(pick, profile):
    profile_tags = (profile or {}).get("tags") or []
    profile_tag_by_id = {t["id"]: t for t in profile_tags}
    pick_tags = pick.get("tags") or []
    shared = [t for t in pick_tags if t["id"] in profile_tag_by_id]
    # Preserve profile order? Use pick order but spec example uses t1+t2 from shared
    resolved = (profile or {}).get("resolved") or []
    seed_names = [r.get("name") or r.get("seed") for r in resolved]
    seed_names_str = ", ".join([s for s in seed_names if s]) or "your seeds"
    affinity = pick.get("affinity")
    if shared:
        t_names = [t["name"] for t in shared[:2]]
        if len(t_names) == 1:
            tag_phrase = t_names[0]
        else:
            tag_phrase = " + ".join(t_names)
        # names of resolved seeds sharing those tags
        shared_ids = {t["id"] for t in shared}
        seed_sharing = []
        for r in resolved:
            r_tag_ids = {t["id"] for t in r.get("tags", [])}
            if r_tag_ids.intersection(shared_ids):
                seed_sharing.append(r.get("name") or r.get("seed"))
        seed_sharing_str = ", ".join(seed_sharing) if seed_sharing else seed_names_str
        aff_str = f"{affinity:.2f}" if isinstance(affinity, (int, float)) else "—"
        # Original spec format when affinity present
        if isinstance(affinity, (int, float)):
            return f"Picked for your {tag_phrase} streak — the same thread that runs through {seed_sharing_str}; taste-graph affinity {affinity:.2f}."
        else:
            return f"Picked for your {tag_phrase} streak — the same thread that runs through {seed_sharing_str}."
    elif isinstance(affinity, (int, float)):
        return f"Surfaced by the taste graph from {seed_names_str} — affinity {affinity:.2f} against your profile."
    else:
        return f"Surfaced from your seeds: {seed_names_str}."


def _enrich(entity, profile):
    if entity is None:
        return None
    return {
        "id": entity.get("id"),
        "name": entity.get("name"),
        "subtype": entity.get("subtype"),
        "description": entity.get("description"),
        "popularity": entity.get("popularity"),
        "affinity": entity.get("affinity"),
        "tags": entity.get("tags") or [],
        "why": _why_for_pick(entity, profile),
    }


def build_plan(client, profile, narrator=None, location=None, refinements=()):
    refinements = list(refinements or ())
    # transport/call counting start
    start_count = None
    if hasattr(client, "call_count"):
        start_count = client.call_count
    transport_calls_start = None
    transport = getattr(client, "transport", None)
    if transport is not None and hasattr(transport, "calls"):
        try:
            transport_calls_start = len(transport.calls)
        except Exception:
            transport_calls_start = None
    # Also handle CacheTransport inner calls? call_count is primary

    resolved_ids = [r["id"] for r in (profile.get("resolved") or [])]
    profile_tags = profile.get("tags") or []
    top_tag_ids = [t["id"] for t in profile_tags[:8]]
    interest_ids = list(profile.get("interest_tag_ids") or [])
    # combine dedup preserving order
    seen = set()
    tag_ids = []
    for tid in top_tag_ids + interest_ids:
        if tid not in seen:
            seen.add(tid)
            tag_ids.append(tid)

    # Build per-slot extra params based on refinements
    # extra_by_slot: slot_name -> dict
    extra_by_slot = {slot: {} for slot, _ in SLOTS}
    changed_by_refinement = {r: False for r in refinements}
    notes = []
    refinements_ignored_set = set()

    # A supplied location always shapes the dinner (place) slot only.
    if location:
        extra_by_slot["dinner"]["filter.location.query"] = location

    for ref in refinements:
        r = str(ref)
        if r == "quieter":
            for slot, _ in SLOTS:
                extra_by_slot[slot]["filter.popularity.max"] = 0.85
            changed_by_refinement[r] = True
        elif r == "closer-to-home":
            if location:
                extra_by_slot["dinner"]["filter.location.query"] = location
                changed_by_refinement[r] = True
            else:
                changed_by_refinement[r] = False
                notes.append("Closer-to-home needs a location — no location was given, so it was ignored.")
        elif r == "date-night":
            # all slots popularity.min
            for slot, _ in SLOTS:
                extra_by_slot[slot]["filter.popularity.min"] = 0.5
            extra_by_slot["watch"]["filter.rating.min"] = 3.8
            extra_by_slot["dinner"]["filter.price_level.min"] = 2
            changed_by_refinement[r] = True
        elif r == "half-the-budget":
            extra_by_slot["dinner"]["filter.price_level.max"] = 2
            changed_by_refinement[r] = True
        else:
            changed_by_refinement[r] = False

    refinements_applied = []
    refinements_ignored = []
    for r in refinements:
        if r not in _KNOWN_REFINEMENTS:
            refinements_ignored.append(r)
        elif changed_by_refinement.get(r):
            refinements_applied.append(r)
        else:
            refinements_ignored.append(r)

    # Honest scope notes
    if location or "closer-to-home" in refinements:
        notes.append("Location shapes the dinner pick only — Qloo location filters apply to places.")
    if refinements_ignored:
        # notes already for closer-to-home; add generic if unknown?
        pass

    slots_out = []
    # If no resolved, picks will be null - still attempt? Spec: all seeds unresolved → plan returns slots with pick null and meta.notes explaining
    # We skip insights calls if no resolved to avoid meaningless picks? But spec says return null picks.
    # Implement: if not resolved_ids and not tag_ids: skip calls, picks null.
    no_signal = not resolved_ids and not tag_ids

    for slot_name, filter_type in SLOTS:
        if no_signal:
            slots_out.append({"slot": slot_name, "type": filter_type, "pick": None, "alternates": []})
            continue
        extra = extra_by_slot.get(slot_name) or {}
        # Only pass extra if non-empty to keep calls clean; client handles empty
        try:
            results = client.insights(filter_type, entity_ids=resolved_ids, tag_ids=tag_ids, extra=extra if extra else None, take=3)
        except Exception:
            results = []
        if not results:
            slots_out.append({"slot": slot_name, "type": filter_type, "pick": None, "alternates": []})
        else:
            pick = _enrich(results[0], profile)
            alternates = [_enrich(r, profile) for r in results[1:]]
            slots_out.append({"slot": slot_name, "type": filter_type, "pick": pick, "alternates": alternates})

    if no_signal:
        notes.append("No seeds could be resolved, so no taste-graph picks could be made — try a film, artist, book, or place you love.")

    # qloo_calls delta
    qloo_calls = 0
    if start_count is not None and hasattr(client, "call_count"):
        qloo_calls = client.call_count - start_count
    elif transport_calls_start is not None and transport is not None and hasattr(transport, "calls"):
        qloo_calls = len(transport.calls) - transport_calls_start

    # transport name: try to infer from client.transport class
    transport_name = "fixture"
    if transport is not None:
        cls = type(transport).__name__
        if cls == "LiveTransport":
            transport_name = "live"
        elif cls == "CacheTransport":
            transport_name = "live"
        elif cls == "FixtureTransport":
            transport_name = "fixture"
        # Also check app may set attribute? fallback
        if hasattr(transport, "inner"):
            inner_cls = type(transport.inner).__name__
            if inner_cls == "LiveTransport":
                transport_name = "live"

    # intro
    temp_plan = {"profile": profile, "slots": slots_out}
    if narrator is None:
        narrator_obj = Narrator("", "gemini-2.5-flash")
    else:
        narrator_obj = narrator
    try:
        intro = narrator_obj.intro(profile, temp_plan)
    except Exception:
        intro = Narrator("", "gemini-2.5-flash").intro(profile, temp_plan)

    plan = {
        "profile": profile,
        "intro": intro,
        "slots": slots_out,
        "meta": {
            "transport": transport_name,
            "qloo_calls": int(qloo_calls),
            "refinements_applied": refinements_applied,
            "refinements_ignored": refinements_ignored,
            "notes": notes,
        },
    }
    return plan
