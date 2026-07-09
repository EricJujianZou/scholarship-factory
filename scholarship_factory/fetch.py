from datetime import datetime, timezone

from pydantic import BaseModel, Field, computed_field


class FetchResult(BaseModel):
    requested_url: str
    final_url: str
    status_code: int | None = None
    content_type: str | None = None
    body: str | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    @computed_field
    @property
    def ok(self) -> bool:
        return (
            self.status_code is not None
            and 200 <= self.status_code < 300
            and self.body is not None
        )
