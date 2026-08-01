"""Read API + dashboard (S7): FastAPI app over the existing store/rank/profile
modules. Extracted facts only - never generates text; missing facts serialize
as null, never invented. Single user (owner="me"), no auth, no writes from the
UI besides the profile editor.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .cli import _default_db_path
from .extract import extract
from .feedback import DecisionStore, DecisionVerdict, PreferenceStore
from .fetch import fetch_url
from .profile import ApplicantProfile, ProfileStore
from .rank import RankedResults, rank
from .relevance import RelevanceStore
from .refresh import RefreshOutcome, refresh_opportunity
from .store import OpportunityStore

_STATIC_DIR = Path(__file__).parent / "static"


class DecisionUpdate(BaseModel):
    verdict: DecisionVerdict
    note: str | None = None


class ProfileUpdate(BaseModel):
    region: str | None = None
    education_level: str | None = None
    field_of_study: str | None = None
    tags: list[str] = []
    bio: str | None = None


def _load_or_create_profile(store: ProfileStore) -> ApplicantProfile:
    existing = store.list()
    if existing:
        return existing[0]
    return store.insert(ApplicantProfile())


def create_app(
    db_path: str | None = None,
    *,
    fetch_fn=fetch_url,
    extract_fn=extract,
) -> FastAPI:
    db_path = db_path or _default_db_path()
    app = FastAPI()

    @app.get("/api/opportunities")
    def get_opportunities() -> dict:
        """Ranked opportunities, annotated with stored fit and any decision.

        Fit comes from the last `sf rank`; this endpoint never calls an LLM, so
        loading the dashboard costs nothing.
        """
        opportunities = OpportunityStore(db_path).list()
        profile = _load_or_create_profile(ProfileStore(db_path))
        ranked = rank(opportunities, profile)
        fits = RelevanceStore(db_path).all()
        decisions = {d.opportunity_id: d for d in DecisionStore(db_path).list()}

        def annotate(item) -> dict:
            data = item.model_dump()
            fit, reason = fits.get(item.opportunity.id, (None, None))
            decision = decisions.get(item.opportunity.id)
            data["fit"] = fit
            data["fit_reason"] = reason
            data["decision"] = decision.verdict.value if decision else None
            return data

        order = {"high": 0, "medium": 1, "low": 2, None: 1}
        eligible = sorted(
            (annotate(i) for i in ranked.eligible),
            key=lambda d: (d["decision"] == "not_interested", order.get(d["fit"], 1)),
        )
        return {
            "eligible": eligible,
            "excluded": [annotate(i) for i in ranked.excluded],
            "preference_summary": PreferenceStore(db_path).get(),
        }

    @app.post("/api/opportunities/{id}/decision")
    def post_decision(id: str, body: DecisionUpdate) -> dict:
        if OpportunityStore(db_path).get(id) is None:
            raise HTTPException(status_code=404, detail="opportunity not found")
        decision = DecisionStore(db_path).set(id, body.verdict, body.note)
        return decision.model_dump()

    @app.post("/api/opportunities/{id}/refresh", response_model=RefreshOutcome)
    def post_refresh(id: str) -> RefreshOutcome:
        store = OpportunityStore(db_path)
        try:
            return refresh_opportunity(
                store, id, fetch_fn=fetch_fn, extract_fn=extract_fn
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="opportunity not found")

    @app.get("/api/profile", response_model=ApplicantProfile)
    def get_profile() -> ApplicantProfile:
        return _load_or_create_profile(ProfileStore(db_path))

    @app.put("/api/profile", response_model=ApplicantProfile)
    def put_profile(body: ProfileUpdate) -> ApplicantProfile:
        store = ProfileStore(db_path)
        existing = _load_or_create_profile(store)
        updated = existing.model_copy(update=body.model_dump())
        return store.update(updated)

    @app.get("/")
    def get_dashboard() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html", media_type="text/html")

    return app
