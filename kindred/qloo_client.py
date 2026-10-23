import hashlib
import json
import os
import unicodedata

import httpx

from . import fixtures_data


class QlooError(Exception):
    pass


VALID_FILTER_TYPES = {
    "urn:entity:movie",
    "urn:entity:tv_show",
    "urn:entity:artist",
    "urn:entity:book",
    "urn:entity:place",
    "urn:entity:destination",
    "urn:entity:podcast",
    "urn:entity:brand",
    "urn:entity:person",
    "urn:entity:tag",
}

_COMMON_FILTERS = {
    "filter.type",
    "filter.tags",
    "filter.exclude.entities",
    "filter.popularity.min",
    "filter.popularity.max",
}
_SIGNALS = {"signal.interests.entities", "signal.interests.tags"}
_OUTPUT = {"take", "page"}

ALLOWLIST = {}
for _ft in VALID_FILTER_TYPES:
    ALLOWLIST[_ft] = set(_SIGNALS) | set(_OUTPUT) | set(_COMMON_FILTERS)
ALLOWLIST["urn:entity:place"] |= {
    "filter.location", "filter.location.query", "filter.location.radius", "filter.address",
    "filter.price_level.min", "filter.price_level.max",
}
ALLOWLIST["urn:entity:destination"] |= {
    "filter.location", "filter.location.query", "filter.location.radius", "filter.address",
}
ALLOWLIST["urn:entity:movie"] |= {
    "filter.rating.min", "filter.rating.max", "filter.release_year.min", "filter.release_year.max", "filter.content_rating",
}
ALLOWLIST["urn:entity:tv_show"] |= {
    "filter.rating.min", "filter.rating.max", "filter.release_year.min", "filter.release_year.max", "filter.content_rating",
}
ALLOWLIST["urn:entity:book"] |= {
    "filter.publication_year.min", "filter.publication_year.max",
}


def _normalize_text(s):
    if s is None:
        return ""
    s = str(s).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s


def normalize_entity(raw):
    if not isinstance(raw, dict):
        return None
    entity_id = raw.get("entity_id") or raw.get("id") or ""
    name = raw.get("name") or ""
    subtype = raw.get("subtype")
    if not subtype:
        types = raw.get("types")
        if isinstance(types, list) and types:
            first = str(types[0])
            subtype = first.split(":")[-1] if ":" in first else first
        elif isinstance(types, str) and types:
            subtype = types.split(":")[-1]
        else:
            subtype = ""
    description = raw.get("short_description") or raw.get("description") or ""
    popularity = raw.get("popularity")
    try:
        popularity = float(popularity) if popularity is not None else 0.0
    except Exception:
        popularity = 0.0
    affinity = raw.get("affinity")
    if affinity is not None:
        try:
            affinity = float(affinity)
        except Exception:
            affinity = None
    tags_raw = raw.get("tags") or []
    tags = []
    for t in tags_raw:
        if isinstance(t, str):
            tags.append({"id": t, "name": t})
        elif isinstance(t, dict):
            tid = t.get("id") or t.get("tag_id") or t.get("urn") or ""
            tname = t.get("name") or tid
            tags.append({"id": tid, "name": tname})
    properties = raw.get("properties") or {}
    if not isinstance(properties, dict):
        properties = {}
    return {
        "id": entity_id,
        "name": name,
        "subtype": subtype,
        "description": description,
        "popularity": popularity,
        "affinity": affinity,
        "tags": tags,
        "properties": properties,
    }


def normalize_tag(raw):
    if isinstance(raw, str):
        return {"id": raw, "name": raw}
    if not isinstance(raw, dict):
        return None
    tid = raw.get("id") or raw.get("tag_id") or raw.get("urn") or ""
    name = raw.get("name") or tid
    return {"id": tid, "name": name}


def _extract_list(payload, kind=None):
    """Tolerate variants: list, dict with results/entities/tags keys."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            return payload["results"]
        if isinstance(payload.get("results"), dict):
            return _extract_list(payload["results"], kind)
        if isinstance(payload.get("entities"), list):
            return payload["entities"]
        if isinstance(payload.get("entities"), dict):
            return _extract_list(payload["entities"], kind)
        if isinstance(payload.get("tags"), list):
            return payload["tags"]
        if isinstance(payload.get("tags"), dict):
            return _extract_list(payload["tags"], kind)
        # dict with entities/tags keys nested under data?
        data = payload.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return _extract_list(data, kind)
        # single entity dict?
        if "id" in payload or "entity_id" in payload or "name" in payload:
            # ambiguous - only if kind indicates single? return []
            return []
    return []


class LiveTransport:
    def __init__(self, base_url, api_key, timeout=15.0):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.timeout = timeout
        self.calls = []

    def get(self, path, params=None):
        params = params or {}
        self.calls.append((path, dict(params)))
        if not self.api_key:
            raise QlooError("QLOO_API_KEY is not configured")
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params=params, headers={"X-Api-Key": self.api_key})
        except QlooError:
            raise
        except Exception as e:
            raise QlooError(str(e)) from e
        if resp.status_code >= 400:
            raise QlooError(f"Qloo HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            return resp.json()
        except Exception as e:
            raise QlooError("Qloo returned non-JSON response") from e


class FixtureTransport:
    def __init__(self):
        self.calls = []

    def get(self, path, params=None):
        params = params or {}
        # record a copy
        self.calls.append((path, dict(params)))
        if path == "/search":
            return self._search(params)
        elif path == "/v2/tags":
            return self._tags(params)
        elif path == "/v2/insights":
            return self._insights(params)
        else:
            return {"results": []}

    def _search(self, params):
        query = params.get("query") or params.get("q") or ""
        qnorm = _normalize_text(query)
        take = params.get("take", 5)
        try:
            take = int(take)
        except Exception:
            take = 5
        types_param = params.get("types") or params.get("type") or ""
        allowed_subtypes = None
        if types_param:
            if isinstance(types_param, (list, tuple)):
                parts = list(types_param)
            else:
                parts = str(types_param).split(",")
            allowed_subtypes = set()
            for p in parts:
                p = str(p).strip()
                if p:
                    allowed_subtypes.add(p.split(":")[-1].lower())
        results = []
        for e in fixtures_data.ENTITIES:
            if allowed_subtypes and e["subtype"].lower() not in allowed_subtypes:
                continue
            names = [e["name"]] + (e.get("aliases") or [])
            matched = False
            if not qnorm:
                matched = True
            else:
                for n in names:
                    if qnorm in _normalize_text(n):
                        matched = True
                        break
            if matched:
                results.append(self._public_entity(e))
        # sort by popularity desc for determinism
        results.sort(key=lambda x: (-x["popularity"], x["name"]))
        return {"results": results[:take]}

    def _tags(self, params):
        query = params.get("query") or params.get("q") or ""
        qnorm = _normalize_text(query)
        take = params.get("take", 10)
        try:
            take = int(take)
        except Exception:
            take = 10
        results = []
        for t in fixtures_data.TAGS:
            if not qnorm or qnorm in _normalize_text(t["name"]) or qnorm in _normalize_text(t["id"]):
                results.append({"id": t["id"], "name": t["name"]})
        return {"results": results[:take]}

    def _insights(self, params):
        filter_type = params.get("filter.type") or ""
        subtype = str(filter_type).split(":")[-1].lower() if filter_type else ""
        take = params.get("take", 6)
        try:
            take = int(take)
        except Exception:
            take = 6

        # signal entities
        sig_entities_raw = params.get("signal.interests.entities") or ""
        if isinstance(sig_entities_raw, (list, tuple)):
            sig_ids = [str(x) for x in sig_entities_raw]
        else:
            sig_ids = [s.strip() for s in str(sig_entities_raw).split(",") if s.strip()] if sig_entities_raw else []
        sig_tags_raw = params.get("signal.interests.tags") or ""
        if isinstance(sig_tags_raw, (list, tuple)):
            sig_tag_ids = [str(x) for x in sig_tags_raw]
        else:
            sig_tag_ids = [s.strip() for s in str(sig_tags_raw).split(",") if s.strip()] if sig_tags_raw else []

        # exclude
        exclude_raw = params.get("filter.exclude.entities") or ""
        if isinstance(exclude_raw, (list, tuple)):
            exclude_ids = set(str(x) for x in exclude_raw)
        else:
            exclude_ids = set(s.strip() for s in str(exclude_raw).split(",") if s.strip()) if exclude_raw else set()
        exclude_ids.update(sig_ids)

        # signal tag set
        signal_tag_ids = set(sig_tag_ids)
        for eid in sig_ids:
            ent = fixtures_data.ENTITY_BY_ID.get(eid)
            if ent:
                for t in ent["tags"]:
                    signal_tag_ids.add(t["id"])

        # filter.tags
        filter_tags_raw = params.get("filter.tags") or ""
        if isinstance(filter_tags_raw, (list, tuple)):
            filter_tag_ids = [str(x) for x in filter_tags_raw]
        else:
            filter_tag_ids = [s.strip() for s in str(filter_tags_raw).split(",") if s.strip()] if filter_tags_raw else []

        def _f(key):
            v = params.get(key)
            if v is None or v == "":
                return None
            try:
                return float(v)
            except Exception:
                return None

        pop_min = _f("filter.popularity.min")
        pop_max = _f("filter.popularity.max")
        price_min = _f("filter.price_level.min")
        price_max = _f("filter.price_level.max")
        rating_min = _f("filter.rating.min")
        rating_max = _f("filter.rating.max")
        pub_min = _f("filter.publication_year.min")
        pub_max = _f("filter.publication_year.max")
        rel_min = _f("filter.release_year.min")
        rel_max = _f("filter.release_year.max")
        loc_query = params.get("filter.location.query") or params.get("filter.location") or ""
        if isinstance(loc_query, dict):
            loc_query = loc_query.get("query") or ""
        loc_query_str = str(loc_query) if loc_query else ""

        candidates = []
        for e in fixtures_data.ENTITIES:
            if subtype and e["subtype"].lower() != subtype:
                continue
            if e["id"] in exclude_ids:
                continue
            props = e.get("properties") or {}
            # popularity
            if pop_min is not None and e["popularity"] < pop_min:
                continue
            if pop_max is not None and e["popularity"] > pop_max:
                continue
            # filter.tags - require at least one if present? Use all? Require any overlap to be lenient
            if filter_tag_ids:
                cand_tag_ids = {t["id"] for t in e["tags"]}
                if not cand_tag_ids.intersection(set(filter_tag_ids)):
                    continue
            # place filters
            if price_min is not None and "price_level" in props:
                if float(props["price_level"]) < price_min:
                    continue
            if price_max is not None and "price_level" in props:
                if float(props["price_level"]) > price_max:
                    continue
            if loc_query_str:
                locality = str(props.get("locality") or "")
                address = str(props.get("address") or "")
                if _normalize_text(loc_query_str) not in _normalize_text(locality) and _normalize_text(loc_query_str) not in _normalize_text(address):
                    continue
            # movie/tv rating
            if rating_min is not None and "rating" in props:
                if float(props["rating"]) < rating_min:
                    continue
            if rating_max is not None and "rating" in props:
                if float(props["rating"]) > rating_max:
                    continue
            if pub_min is not None and "publication_year" in props:
                if float(props["publication_year"]) < pub_min:
                    continue
            if pub_max is not None and "publication_year" in props:
                if float(props["publication_year"]) > pub_max:
                    continue
            if rel_min is not None and "release_year" in props:
                if float(props["release_year"]) < rel_min:
                    continue
            if rel_max is not None and "release_year" in props:
                if float(props["release_year"]) > rel_max:
                    continue
            # content_rating
            cr = params.get("filter.content_rating")
            if cr and "content_rating" in props:
                if str(props["content_rating"]) != str(cr):
                    continue

            cand_tag_ids = [t["id"] for t in e["tags"]]
            if cand_tag_ids and signal_tag_ids:
                cand_set = set(cand_tag_ids)
                overlap = len(cand_set.intersection(signal_tag_ids))
                union = len(cand_set.union(signal_tag_ids))
                overlap_ratio = overlap / union if union else 0.0
            else:
                overlap_ratio = 0.0
            affinity = 0.55 + 0.44 * overlap_ratio
            pub = self._public_entity(e)
            pub["affinity"] = round(affinity, 4)
            candidates.append(pub)

        candidates.sort(key=lambda x: (-x["affinity"], -x["popularity"], x["name"]))
        return {"results": candidates[:take]}

    def _public_entity(self, e):
        return {
            "id": e["id"],
            "name": e["name"],
            "subtype": e["subtype"],
            "description": e["description"],
            "popularity": e["popularity"],
            "tags": [{"id": t["id"], "name": t["name"]} for t in e["tags"]],
            "properties": dict(e.get("properties") or {}),
        }


class CacheTransport:
    def __init__(self, inner, cache_dir):
        self.inner = inner
        self.cache_dir = cache_dir
        self.calls = getattr(inner, "calls", [])

    def get(self, path, params=None):
        params = params or {}
        os.makedirs(self.cache_dir, exist_ok=True)
        key_src = path + "|" + json.dumps(params, sort_keys=True, default=str)
        key = hashlib.sha256(key_src.encode("utf-8")).hexdigest()
        fp = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        result = self.inner.get(path, params)
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass
        return result


class QlooClient:
    def __init__(self, transport):
        self.transport = transport
        self.last_dropped_params = []
        self.call_count = 0

    def _get(self, path, params):
        self.call_count += 1
        return self.transport.get(path, params)

    def search(self, query, types=None, take=5):
        params = {"query": query, "take": take}
        if types:
            if isinstance(types, (list, tuple)):
                params["types"] = ",".join(types)
            else:
                params["types"] = types
        payload = self._get("/search", params)
        raw_list = _extract_list(payload)
        out = []
        for r in raw_list:
            n = normalize_entity(r)
            if n:
                # fixture/live may not include affinity
                if n.get("affinity") is None and isinstance(r, dict) and "affinity" in r:
                    n["affinity"] = r["affinity"]
                out.append(n)
        return out[:take] if take else out

    def tags(self, query, take=10):
        params = {"query": query, "take": take}
        payload = self._get("/v2/tags", params)
        raw_list = _extract_list(payload)
        out = []
        for r in raw_list:
            n = normalize_tag(r)
            if n:
                out.append(n)
        return out[:take] if take else out

    def insights(self, filter_type, entity_ids=None, tag_ids=None, extra=None, take=6):
        if filter_type not in VALID_FILTER_TYPES:
            raise ValueError(f"Invalid filter_type: {filter_type}")
        self.last_dropped_params = []
        params = {"filter.type": filter_type, "take": take}
        if entity_ids:
            params["signal.interests.entities"] = ",".join(entity_ids)
        if tag_ids:
            params["signal.interests.tags"] = ",".join(tag_ids)
        if extra:
            allow = ALLOWLIST.get(filter_type, set())
            for k, v in extra.items():
                if k in allow:
                    params[k] = v
                else:
                    self.last_dropped_params.append(k)
        payload = self._get("/v2/insights", params)
        raw_list = _extract_list(payload)
        out = []
        for r in raw_list:
            n = normalize_entity(r)
            if n:
                out.append(n)
        return out[:take] if take else out
