import json
import re

import httpx


class Narrator:
    def __init__(self, google_api_key, model="gemini-2.5-flash"):
        self.google_api_key = google_api_key or ""
        self.model = model or "gemini-2.5-flash"

    def available(self):
        return bool(self.google_api_key)

    def _template_intro(self, profile, plan):
        tags = (profile or {}).get("tags") or []
        top_tag = tags[0]["name"] if tags else "signature"
        slots = {}
        if isinstance(plan, dict):
            for s in plan.get("slots") or []:
                pick = s.get("pick") if isinstance(s, dict) else None
                name = pick.get("name") if isinstance(pick, dict) and pick else "an open slot"
                slots[s.get("slot")] = name
        dinner = slots.get("dinner", "an open slot")
        watch = slots.get("watch", "an open slot")
        listen = slots.get("listen", "an open slot")
        read = slots.get("read", "an open slot")
        return f"An evening tuned to your {top_tag} streak: {dinner}, {watch}, {listen}, and {read}."

    def intro(self, profile, plan):
        if not self.available():
            return self._template_intro(profile, plan)
        # Build prompt
        tags = (profile or {}).get("tags") or []
        tag_names = ", ".join(t["name"] for t in tags[:6])
        picks = []
        if isinstance(plan, dict):
            for s in plan.get("slots") or []:
                pick = s.get("pick") if isinstance(s, dict) else None
                if pick:
                    picks.append(f"{s.get('slot')}: {pick.get('name')}")
        prompt = (
            f"Write ONE warm sentence (max 30 words) introducing an evening plan. "
            f"Taste tags: {tag_names}. Picks: {'; '.join(picks)}. "
            f"Return only the sentence, no quotes."
        )
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(
                    url,
                    headers={"x-goog-api-key": self.google_api_key, "Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                )
            if resp.status_code >= 400:
                return self._template_intro(profile, plan)
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = str(text).strip()
            if not text:
                return self._template_intro(profile, plan)
            return text
        except Exception:
            return self._template_intro(profile, plan)

    def generic_plan(self, seeds):
        if not self.available():
            return None
        seed_str = ", ".join(str(s) for s in (seeds or []))
        prompt = (
            f"Given only these favorite names: {seed_str}, suggest a generic popular evening plan. "
            f"Respond with ONLY JSON in the form "
            f'{{"slots": [{{"slot": "dinner", "name": "...", "why": "..."}}, '
            f'{{"slot": "watch", "name": "...", "why": "..."}}, '
            f'{{"slot": "listen", "name": "...", "why": "..."}}, '
            f'{{"slot": "read", "name": "...", "why": "..."}}]}} '
            f"with one-line reasons. No other text."
        )
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(
                    url,
                    headers={"x-goog-api-key": self.google_api_key, "Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                )
            if resp.status_code >= 400:
                return None
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = str(text).strip()
            # try JSON extraction
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, dict) and "slots" in parsed:
                    return parsed
                if isinstance(parsed, dict):
                    return parsed
            return None
        except Exception:
            return None
