from enum import Enum

from pydantic import BaseModel, Field, model_validator
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

    deadline_source: str | None = None
    reward_source: str | None = None
    cost_source: str | None = None
    source_observed_date: str | None = None

    owner: str = "me"
    status: str = "new"

    first_seen: str | None = None
    last_seen: str | None = None

    @model_validator(mode="after")
    def _require_source_for_provenance(self) -> "Opportunity":
        for provenance, source, name in (
            (self.deadline_provenance, self.deadline_source, "deadline"),
            (self.reward_provenance, self.reward_source, "reward"),
            (self.cost_provenance, self.cost_source, "cost"),
        ):
            if provenance != Provenance.NONE and source is None:
                raise ValueError(
                    f"{name}_source is required when {name}_provenance is not 'none'"
                )
        return self
