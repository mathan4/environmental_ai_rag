"""
Shared text rendering for a synthesize_response() result. Used in two places:
1. main.py's CLI display (what the user sees)
2. core/engine.py's conversation history (what the LLM sees on the NEXT turn)

Having one renderer matters specifically for #2 — previously the history stored a raw
Python list-of-dicts repr() of the recommendations, which is much harder for the model
to read back and build on than clean text. Now both get the same readable format.
"""


def render_result_text(result: dict) -> str:
    if result.get("clarifying_question"):
        return f"[Asked clarifying question]: {result['clarifying_question']}"

    if result.get("reply"):
        # Conversational prose mode — a direct answer, not a recommendation card set.
        return result["reply"]

    lines = []
    for i, rec in enumerate(result.get("recommendations", []), 1):
        lines.append(f"[{i}] {rec.get('action')}")
        lines.append(f"    Why: {rec.get('why')}")
        lines.append(f"    Impacted metrics: {', '.join(rec.get('impacted_metrics', []))}")
        if rec.get("estimated_effect"):
            lines.append(f"    Estimated effect: {rec['estimated_effect']}")
        lines.append(f"    Time horizon: {rec.get('time_horizon')} ({rec.get('time_horizon_detail', '')})")
        lines.append(f"    Confidence: {rec.get('confidence')}")
        if rec.get("source"):
            lines.append(f"    Source: {rec['source']}")

    if result.get("variable_links"):
        lines.append("Cross-variable links considered:")
        for link in result["variable_links"]:
            lines.append(f"  - {link}")

    return "\n".join(lines) if lines else "[No recommendations generated]"