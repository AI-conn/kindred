import os


def _env(name, default=""):
    v = os.environ.get(name)
    return default if v is None else v


QLOO_API_KEY = _env("QLOO_API_KEY", "")
QLOO_BASE_URL = _env("QLOO_BASE_URL", "https://hackathon.api.qloo.com")
QLOO_TRANSPORT = _env("QLOO_TRANSPORT", "auto")  # auto|live|fixture
GOOGLE_API_KEY = _env("GOOGLE_API_KEY", "")
KINDRED_LLM_MODEL = _env("KINDRED_LLM_MODEL", "gemini-2.5-flash")
KINDRED_CACHE_DIR = _env("KINDRED_CACHE_DIR", "data/cache")


def _port():
    try:
        return int(os.environ.get("PORT", "7860"))
    except ValueError:
        return 7860


PORT = _port()


def resolve_transport_name():
    t = (QLOO_TRANSPORT or "auto").strip().lower()
    if t == "live":
        return "live"
    if t == "fixture":
        return "fixture"
    # auto
    return "live" if QLOO_API_KEY else "fixture"
