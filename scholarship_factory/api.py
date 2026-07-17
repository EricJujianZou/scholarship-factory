"""Read API + dashboard (S7): FastAPI app over the existing store/rank/profile
modules. Extracted facts only - never generates text; missing facts serialize
as null, never invented. Single user (owner="me"), no auth, no writes from the
UI besides the profile editor.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .cli import _default_db_path
from .profile import ApplicantProfile, ProfileStore
from .rank import RankedResults, rank
from .store import OpportunityStore

_STATIC_DIR = Path(__file__).parent / "static"


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


def create_app(db_path: str | None = None) -> FastAPI:
    db_path = db_path or _default_db_path()
    app = FastAPI()

    @app.get("/api/opportunities", response_model=RankedResults)
    def get_opportunities() -> RankedResults:
        opportunities = OpportunityStore(db_path).list()
        profile = _load_or_create_profile(ProfileStore(db_path))
        return rank(opportunities, profile)

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
