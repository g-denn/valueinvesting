from __future__ import annotations

from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Document, Idea, Source, UserTag
from .schemas import (
    DocumentOut,
    IdeaOut,
    IdeaPatch,
    PasteIngestRequest,
    SearchResponse,
    SourceIn,
    SourceOut,
    ReferenceBootstrapRequest,
    ReferenceBootstrapResult,
    SubstackBootstrapRequest,
    SubstackBootstrapResult,
    TagRequest,
    URLIngestRequest,
)
from .services.pipeline import ingest_text
from .services.reference_sources import load_reference_sources, reference_source_name
from .services.substack import (
    load_default_substack_sources,
    source_name_from_url,
    source_to_rss_url,
    normalize_source_url,
)

app = FastAPI(title="Idea Radar MVP", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)






@app.post("/sources/reference/bootstrap", response_model=ReferenceBootstrapResult)
def bootstrap_reference_sources(payload: ReferenceBootstrapRequest, db: Session = Depends(get_db)):
    urls: list[str] = []
    if payload.use_default_file:
        urls.extend(load_reference_sources())
    if payload.urls:
        urls.extend(payload.urls)

    seen: set[str] = set()
    norm_urls: list[str] = []
    for url in urls:
        nurl = normalize_source_url(url)
        if nurl in seen:
            continue
        seen.add(nurl)
        norm_urls.append(nurl)

    created = 0
    existing = 0
    out_sources: list[Source] = []

    for base_url in norm_urls:
        found = db.scalar(select(Source).where(Source.base_url == base_url))
        if found:
            existing += 1
            out_sources.append(found)
            continue

        source = Source(
            name=reference_source_name(base_url),
            source_type="reference_site",
            base_url=base_url,
            rss_url=None,
            policy_tag="public_reference",
        )
        db.add(source)
        db.flush()
        out_sources.append(source)
        created += 1

    db.commit()
    return ReferenceBootstrapResult(
        created=created,
        existing=existing,
        sources=[SourceOut.model_validate(s) for s in out_sources],
    )

@app.post("/sources/substack", response_model=SourceOut)
def add_substack_source(payload: SourceIn, db: Session = Depends(get_db)):
    base_url = normalize_source_url(payload.url)
    name = source_name_from_url(base_url)
    existing = db.scalar(select(Source).where(Source.base_url == base_url))
    if existing:
        return existing

    source = Source(
        name=name,
        source_type="substack_rss",
        base_url=base_url,
        rss_url=source_to_rss_url(base_url),
        policy_tag="public_rss",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@app.post("/sources/substack/bootstrap", response_model=SubstackBootstrapResult)
def bootstrap_substack_sources(payload: SubstackBootstrapRequest, db: Session = Depends(get_db)):
    urls: list[str] = []
    if payload.use_default_file:
        urls.extend(load_default_substack_sources())
    if payload.urls:
        urls.extend(payload.urls)

    # stable dedup in-order
    seen: set[str] = set()
    norm_urls: list[str] = []
    for url in urls:
        nurl = normalize_source_url(url)
        if nurl in seen:
            continue
        seen.add(nurl)
        norm_urls.append(nurl)

    created = 0
    existing = 0
    out_sources: list[Source] = []

    for base_url in norm_urls:
        found = db.scalar(select(Source).where(Source.base_url == base_url))
        if found:
            existing += 1
            out_sources.append(found)
            continue

        source = Source(
            name=source_name_from_url(base_url),
            source_type="substack_rss",
            base_url=base_url,
            rss_url=source_to_rss_url(base_url),
            policy_tag="public_rss",
        )
        db.add(source)
        db.flush()
        out_sources.append(source)
        created += 1

    db.commit()
    return SubstackBootstrapResult(
        created=created,
        existing=existing,
        sources=[SourceOut.model_validate(s) for s in out_sources],
    )

@app.post("/documents/url", response_model=DocumentOut)
def ingest_url(payload: URLIngestRequest, db: Session = Depends(get_db)):
    text = payload.raw_text or f"Imported URL: {payload.url}"
    doc = ingest_text(db, source_name=payload.source_name, text=text, title=str(payload.url), url=str(payload.url))
    db.commit()
    db.refresh(doc)
    return doc


@app.post("/documents/paste", response_model=DocumentOut)
def ingest_paste(payload: PasteIngestRequest, db: Session = Depends(get_db)):
    doc = ingest_text(db, source_name=payload.source_name, text=payload.text, title=payload.title)
    db.commit()
    db.refresh(doc)
    return doc


@app.post("/documents/upload", response_model=DocumentOut)
async def ingest_upload(source_name: str = "upload", file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = (await file.read()).decode("utf-8", errors="ignore")
    doc = ingest_text(db, source_name=source_name, text=content, title=file.filename)
    db.commit()
    db.refresh(doc)
    return doc


@app.get("/feed", response_model=list[DocumentOut])
def feed(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.scalars(select(Document).order_by(Document.quality_score.desc(), Document.created_at.desc()).limit(limit)).all()
    return rows


@app.get("/ideas/{idea_id}", response_model=IdeaOut)
def get_idea(idea_id: int, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@app.get("/search", response_model=SearchResponse)
def search(q: str, db: Session = Depends(get_db)):
    qlike = f"%{q}%"
    rows = db.scalars(
        select(Document).where(
            or_(
                Document.title.ilike(qlike),
                Document.clean_text.ilike(qlike),
                Document.raw_text.ilike(qlike),
            )
        )
    ).all()
    return SearchResponse(documents=rows)


@app.patch("/ideas/{idea_id}", response_model=IdeaOut)
def patch_idea(idea_id: int, payload: IdeaPatch, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    idea.one_line_thesis = payload.one_line_thesis
    idea.thesis_summary = payload.thesis_summary
    idea.catalysts = payload.catalysts
    idea.risks = payload.risks
    idea.valuation_claim = payload.valuation_claim
    db.commit()
    db.refresh(idea)
    return idea


@app.post("/ideas/{idea_id}/tags")
def add_tag(idea_id: int, payload: TagRequest, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    tag = UserTag(document_id=idea.document_id, tag=payload.tag, note=payload.note)
    db.add(tag)
    db.commit()
    return {"status": "ok", "tag_id": tag.id}


@app.get("/digests/weekly/latest")
def latest_digest(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=7)
    docs = db.scalars(
        select(Document)
        .where(Document.created_at >= cutoff)
        .order_by(Document.quality_score.desc())
        .limit(10)
    ).all()
    return {
        "period_days": 7,
        "generated_at": datetime.utcnow().isoformat(),
        "top_documents": [DocumentOut.model_validate(d).model_dump() for d in docs],
    }
