import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

from . import config
from .qloo_client import QlooClient, LiveTransport, FixtureTransport, CacheTransport
from .taste import PERSONAS, build_profile
from .narrate import Narrator
from .planner import build_plan
from .compare import compare as compare_fn

app = FastAPI(title="Kindred")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Client construction from config at startup
_transport_name = config.resolve_transport_name()
if _transport_name == "live":
    _live = LiveTransport(config.QLOO_BASE_URL, config.QLOO_API_KEY)
    _transport = CacheTransport(_live, config.KINDRED_CACHE_DIR)
else:
    _transport = FixtureTransport()

_client = QlooClient(_transport)
_narrator = Narrator(config.GOOGLE_API_KEY, config.KINDRED_LLM_MODEL)

app.state.transport_name = _transport_name
app.state.transport = _transport
app.state.client = _client
app.state.narrator = _narrator


def get_client():
    return app.state.client


def get_narrator():
    return app.state.narrator


def get_transport_name():
    return app.state.transport_name


class ProfileRequest(BaseModel):
    seeds: Optional[List[str]] = None
    interest_words: Optional[List[str]] = None


class PlanRequest(BaseModel):
    seeds: Optional[List[str]] = None
    interest_words: Optional[List[str]] = None
    location: Optional[str] = None
    refinements: Optional[List[str]] = None


class CompareRequest(BaseModel):
    seeds: Optional[List[str]] = None
    interest_words: Optional[List[str]] = None
    location: Optional[str] = None
    refinements: Optional[List[str]] = None


def _validate_seeds(seeds):
    if not seeds or not isinstance(seeds, list) or len([s for s in seeds if str(s).strip()]) == 0:
        return JSONResponse(status_code=422, content={"detail": "Give me at least one favorite to start from."})
    return None


def _profile_public(profile):
    return {
        "resolved": profile.get("resolved") or [],
        "unresolved": profile.get("unresolved") or [],
        "tags": profile.get("tags") or [],
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "transport": get_transport_name(),
        "qloo_key_configured": bool(config.QLOO_API_KEY),
        "llm_configured": bool(config.GOOGLE_API_KEY),
    }


@app.get("/api/personas")
def personas():
    return {"personas": [{"id": p["id"], "label": p["label"], "seeds": p["seeds"]} for p in PERSONAS]}


@app.post("/api/profile")
def profile_endpoint(req: ProfileRequest):
    err = _validate_seeds(req.seeds)
    if err:
        return err
    profile = build_profile(get_client(), req.seeds, interest_words=req.interest_words)
    return _profile_public(profile)


@app.post("/api/plan")
def plan_endpoint(req: PlanRequest):
    err = _validate_seeds(req.seeds)
    if err:
        return err
    profile = build_profile(get_client(), req.seeds, interest_words=req.interest_words)
    plan = build_plan(get_client(), profile, narrator=get_narrator(), location=req.location, refinements=req.refinements or ())
    # Return the full plan; its profile carries resolved/unresolved/tags
    # (plus internal seeds/interest ids used by compare, which do not
    # conflict with the documented profile fields).
    return plan


@app.post("/api/compare")
def compare_endpoint(req: CompareRequest):
    err = _validate_seeds(req.seeds)
    if err:
        return err
    profile = build_profile(get_client(), req.seeds, interest_words=getattr(req, "interest_words", None))
    result = compare_fn(get_client(), profile, get_narrator(), location=req.location)
    return result


# Mount static if exists - app/static relative to app/ (parent of kindred package)
_static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
