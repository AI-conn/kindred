---
title: Kindred
emoji: 🍷
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 7860
license: house — PATTO / reserved
---

# Kindred — plans your evening from your taste

## What it is

Kindred is a taste-graph concierge: you seed it with a few favourites — a film, an artist, a book — and it plans a cross-domain evening (dinner, something to watch, something to listen to, something to read). Every pick carries a "why this fits you" evidence line, so the plan reads as reasoning about your taste rather than a popularity chart.

## How it uses Qloo

- **Search** resolves each favourite you type to a real entity in the Qloo taste graph.
- **Tags** resolves interest words to taste tags, which become part of your taste profile alongside the tags attached to your resolved favourites.
- **Insights** runs across place, movie, artist, and book, using entity and tag signals together to find picks in each domain.
- Every pick carries an evidence line computed from the tags it shares with your profile and the affinity returned in the Qloo response.

Kindred also includes a with/without-Qloo comparison mode: the same seeds are planned a second way, without any Qloo data, and the two plans are shown side by side with a count of evidence-backed picks and taste tags used. The baseline is deliberately plain — it shows, honestly, what the taste graph adds and what planning looks like without it.

## Architecture

A FastAPI backend serves the single-page frontend and holds all API keys server-side; keys are never sent to the browser. Qloo responses are kept in a private, server-side cache. A language model is used only for conversational narration, with a deterministic fallback when no model is configured — the picks themselves are computed from Qloo data, never from the language model.

## Run locally

```bash
pip install -r requirements.txt
```

Set the environment variables described in `.env.example` (at minimum `QLOO_API_KEY` for live results), then:

```bash
uvicorn kindred.main:app --port 7860
```

Open <http://localhost:7860>.

## Development without a key

Setting `QLOO_TRANSPORT=fixture` runs the app on built-in synthetic sample data, for development and tests. Fixture mode is clearly labeled in the UI with a "Demo data mode" badge. Live mode is the default whenever a Qloo API key is configured.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Deploy

Kindred deploys as a Docker Space on Hugging Face Spaces, using the included `Dockerfile`. Set `QLOO_API_KEY` — and optionally `GOOGLE_API_KEY` for narration — as Space secrets in the Space settings, never as files in the repository.

## License

House license — see `LICENSE`.
