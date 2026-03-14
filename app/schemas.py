from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class URLIngestRequest(BaseModel):
    url: HttpUrl
    source_name: str = "manual"
    raw_text: str | None = None


class PasteIngestRequest(BaseModel):
    source_name: str = "paste"
    title: str | None = None
    text: str = Field(min_length=20)


class IdeaCard(BaseModel):
    company: str | None = None
    ticker: str | None = None
    one_line_thesis: str
    thesis_bullets: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    valuation_claim: str = ""
    extraction_confidence: float = 0.0


class DocumentOut(BaseModel):
    id: int
    url: str | None
    title: str | None
    status: str
    direction: str | None
    quality_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class IdeaPatch(BaseModel):
    one_line_thesis: str
    thesis_summary: list[str]
    catalysts: list[str]
    risks: list[str]
    valuation_claim: str


class IdeaOut(BaseModel):
    id: int
    document_id: int
    one_line_thesis: str
    thesis_summary: list[str]
    catalysts: list[str]
    risks: list[str]
    valuation_claim: str
    extraction_confidence: float

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    documents: list[DocumentOut]


class TagRequest(BaseModel):
    tag: str
    note: str | None = None


class SourceIn(BaseModel):
    url: str


class SubstackBootstrapRequest(BaseModel):
    urls: list[str] | None = None
    use_default_file: bool = True


class SourceOut(BaseModel):
    id: int
    name: str
    source_type: str
    base_url: str | None
    rss_url: str | None
    policy_tag: str

    class Config:
        from_attributes = True


class SubstackBootstrapResult(BaseModel):
    created: int
    existing: int
    sources: list[SourceOut]


class ReferenceBootstrapRequest(BaseModel):
    urls: list[str] | None = None
    use_default_file: bool = True


class ReferenceBootstrapResult(BaseModel):
    created: int
    existing: int
    sources: list[SourceOut]
