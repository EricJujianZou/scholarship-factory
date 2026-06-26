from enum import Enum

from pydantic import BaseModel, Field
from uuid import uuid4


class Provenance(str, Enum):
    QUOTED = "quoted"
    DERIVED = "derived"
    NONE = "none"


class Opportunity(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    apply_url: str
    source_url: str

    deadline: str | None = None
    reward: str | None = None
    cost: str | None = None
    organization: str | None = None
    requirements: str | None = None
    type: str | None = None
    description: str | None = None

    deadline_provenance: Provenance = Provenance.NONE
    reward_provenance: Provenance = Provenance.NONE
    cost_provenance: Provenance = Provenance.NONE

    owner: str = "me"
    status: str = "new"

    first_seen: str | None = None
    last_seen: str | None = None
