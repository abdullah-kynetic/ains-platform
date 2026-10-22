"""Source references used by manual auditor review, independent of model providers."""

from pydantic import BaseModel, Field


class Citation(BaseModel):
    page: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=1000)
