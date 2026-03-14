from __future__ import annotations


def compute_quality_score(clean_text: str, thesis_bullets: list[str], catalysts: list[str], risks: list[str]) -> float:
    # Deterministic MVP heuristic; replace with model-driven scoring later.
    length_score = min(len(clean_text) / 5000, 1.0)
    structure_score = min((len(thesis_bullets) + len(catalysts) + len(risks)) / 12, 1.0)
    signal_score = 0.6 * structure_score + 0.4 * length_score
    return round(signal_score, 4)
