from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Document, Idea, Source
from app.services.dedup import fingerprint
from app.services.extraction import detect_direction, extract_idea_card
from app.services.scoring import compute_quality_score


def get_or_create_source(db: Session, name: str) -> Source:
    source = db.scalar(select(Source).where(Source.name == name))
    if source:
        return source
    source = Source(name=name, source_type="manual")
    db.add(source)
    db.flush()
    return source


def ingest_text(db: Session, *, source_name: str, text: str, title: str | None = None, url: str | None = None) -> Document:
    source = get_or_create_source(db, source_name)
    doc = Document(
        source_id=source.id,
        url=url,
        title=title,
        raw_text=text,
        clean_text=text.strip(),
        fingerprint=fingerprint(text),
        status="PARSED",
    )
    db.add(doc)
    db.flush()
    process_document(db, doc)
    return doc


def process_document(db: Session, doc: Document) -> Document:
    text = doc.clean_text or doc.raw_text
    doc.direction = detect_direction(text)

    # Dedup check
    dup = db.scalar(select(Document).where(Document.fingerprint == doc.fingerprint, Document.id != doc.id))
    if dup:
        doc.status = "INDEXED"
        doc.quality_score = max(dup.quality_score - 0.05, 0)
        return doc

    idea_card = extract_idea_card(text, title=doc.title)

    company_id = None
    if idea_card.company:
        company = db.scalar(select(Company).where(Company.name == idea_card.company))
        if not company:
            company = Company(name=idea_card.company, ticker=idea_card.ticker)
            db.add(company)
            db.flush()
        company_id = company.id

    idea = Idea(
        document_id=doc.id,
        company_id=company_id,
        one_line_thesis=idea_card.one_line_thesis,
        thesis_summary=idea_card.thesis_bullets,
        catalysts=idea_card.catalysts,
        risks=idea_card.risks,
        valuation_claim=idea_card.valuation_claim,
        extraction_confidence=idea_card.extraction_confidence,
    )
    db.add(idea)

    doc.quality_score = compute_quality_score(text, idea_card.thesis_bullets, idea_card.catalysts, idea_card.risks)
    doc.status = "INDEXED"
    db.flush()
    return doc
