from __future__ import annotations

import re
from app.schemas import IdeaCard

TICKER_RE = re.compile(r"\b([A-Z]{1,5})(?::[A-Z]{1,5})?\b")


def extract_idea_card(text: str, title: str | None = None) -> IdeaCard:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    first_sentence = (lines[0] if lines else text[:180]).strip()

    bullets = [ln.lstrip("-• ") for ln in lines if ln.startswith(("-", "•"))][:5]
    if not bullets:
        bullets = [s.strip() for s in re.split(r"[.;]", text) if len(s.strip()) > 40][:5]

    lower = text.lower()
    catalysts = []
    risks = []

    for sentence in re.split(r"(?<=[.!?])\s+", text):
        s = sentence.strip()
        sl = s.lower()
        if any(k in sl for k in ["catalyst", "trigger", "upside", "re-rate"]):
            catalysts.append(s)
        if any(k in sl for k in ["risk", "downside", "bear", "failure", "could be wrong"]):
            risks.append(s)

    ticker_match = TICKER_RE.search(text)
    ticker = ticker_match.group(1) if ticker_match else None

    valuation = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if any(k in sentence.lower() for k in ["valuation", "multiple", "ev/", "discount", "intrinsic value"]):
            valuation = sentence.strip()
            break

    confidence = 0.5
    if len(text) > 1000:
        confidence += 0.15
    if bullets:
        confidence += 0.15
    if catalysts or risks:
        confidence += 0.1

    return IdeaCard(
        company=title,
        ticker=ticker,
        one_line_thesis=first_sentence[:280],
        thesis_bullets=bullets,
        catalysts=catalysts[:5],
        risks=risks[:5],
        valuation_claim=valuation,
        extraction_confidence=min(confidence, 0.95),
    )


def detect_direction(text: str) -> str:
    t = text.lower()
    if "short" in t and "long" not in t:
        return "short"
    if "long" in t:
        return "long"
    return "watchlist"
