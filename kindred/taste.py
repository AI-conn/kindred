from collections import Counter

PERSONAS = [
    {"id": "indie-film-night", "label": "Indie film + natural wine", "seeds": ["The Grand Budapest Hotel", "Phoebe Bridgers", "Norwegian Wood"]},
    {"id": "jazz-and-old-books", "label": "Jazz + old bookstores", "seeds": ["Miles Davis", "The Master and Margarita", "Spirited Away"]},
    {"id": "skate-punk-ramen", "label": "Skate punk + ramen", "seeds": ["Descendents", "Whiplash", "Convenience Store Woman"]},
]

_TYPE_MAP = {
    "movie": "urn:entity:movie",
    "film": "urn:entity:movie",
    "tv": "urn:entity:tv_show",
    "tv_show": "urn:entity:tv_show",
    "artist": "urn:entity:artist",
    "music": "urn:entity:artist",
    "book": "urn:entity:book",
    "place": "urn:entity:place",
    "destination": "urn:entity:destination",
    "podcast": "urn:entity:podcast",
    "brand": "urn:entity:brand",
    "person": "urn:entity:person",
}


def build_profile(client, seeds, interest_words=None):
    resolved = []
    unresolved = []
    seeds_list = list(seeds or [])
    for seed in seeds_list:
        raw_seed = str(seed)
        query = raw_seed
        types = None
        if ":" in raw_seed:
            prefix, rest = raw_seed.split(":", 1)
            prefix_key = prefix.strip().lower()
            # Only treat as type prefix if prefix is a known type label and rest non-empty
            # Also handle full URN prefix like "urn:entity:movie: Name" - unlikely; check simple map first
            if prefix_key in _TYPE_MAP and rest.strip():
                query = rest.strip()
                types = [_TYPE_MAP[prefix_key]]
            elif prefix_key == "urn":
                # not a simple type prefix, keep as is
                pass
        try:
            results = client.search(query, types=types, take=5)
        except Exception:
            results = []
        if not results:
            unresolved.append(raw_seed)
            continue
        # pick highest-popularity match
        best = max(results, key=lambda x: x.get("popularity") or 0)
        resolved.append({
            "seed": raw_seed,
            "id": best["id"],
            "name": best["name"],
            "subtype": best.get("subtype") or "",
            "tags": [{"id": t["id"], "name": t["name"]} for t in best.get("tags", [])],
        })

    # tag frequency
    counter = Counter()
    name_by_id = {}
    for ent in resolved:
        for t in ent["tags"]:
            counter[t["id"]] += 1
            name_by_id[t["id"]] = t["name"]
    sorted_tags = sorted(counter.items(), key=lambda kv: (-kv[1], name_by_id[kv[0]]))
    tags = [{"id": tid, "name": name_by_id[tid], "weight": count} for tid, count in sorted_tags[:10]]

    interest_tag_ids = []
    if interest_words:
        seen = set()
        for word in interest_words:
            try:
                matched = client.tags(str(word), take=10)
            except Exception:
                matched = []
            if matched:
                # take first match as resolution for that word
                tid = matched[0]["id"]
                if tid not in seen:
                    seen.add(tid)
                    interest_tag_ids.append(tid)

    profile = {
        "seeds": seeds_list,
        "resolved": resolved,
        "unresolved": unresolved,
        "tags": tags,
        "interest_tag_ids": interest_tag_ids,
    }
    return profile
