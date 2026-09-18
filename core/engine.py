"""
End-to-end orchestration:
1. Extract/merge structured fields from the user's text (or accept structured JSON directly)
2. Check for missing required fields -> if any, ask a clarifying question (no guessing)
3. Run multi-metric reasoning to find linked cross-variable issues
4. Retrieve structured interventions + semantic passages based on those issues
5. Synthesize the final evidence-backed response via Groq (numbers/sources constrained
   to what was retrieved)
6. Update conversation memory
"""
from conversation.memory import get_session
from conversation.input_parser import extract_fields
from reasoning.multi_metric_engine import analyze, missing_required_fields
from rag.retriever import get_structured_interventions, semantic_search
from llm.groq_client import synthesize_response
from core.formatting import render_result_text


def handle_message(user_text: str, session_id: str = "default", structured_input: dict = None) -> dict:
    session = get_session(session_id)
    session.add_turn("user", user_text)

    # Structured JSON input (if provided) takes priority over text extraction for those fields.
    # pending_fields carries over from the last turn's clarifying question, so a bare
    # reply like "low" is understood as answering it even without restating the field name.
    extracted = extract_fields(user_text, pending_fields=session.pending_fields)
    if structured_input:
        extracted.update(structured_input)
    session.update_inputs(extracted)

    inputs = session.snapshot()
    missing = missing_required_fields(inputs)

    if missing:
        session.pending_fields = missing
        result = synthesize_response(
            user_query=user_text, inputs=inputs, analysis={"issues": [], "linked_variables": []},
            structured_evidence=[], semantic_evidence=[], missing_fields=missing,
            conversation_history=session.history,
        )
        session.add_turn("assistant", result.get("clarifying_question", ""))
        return result

    session.pending_fields = []

    analysis = analyze(inputs)

    structured_evidence = get_structured_interventions(
        land_use=inputs.get("land_use"),
        rainfall=inputs.get("rainfall_level"),
        soc=inputs.get("soil_organic_carbon_pct"),
    )

    # Build a semantic query from the detected issues so retrieval is targeted, not generic.
    issue_terms = " ".join(i["issue"].replace("_", " ") for i in analysis["issues"]) or user_text
    semantic_evidence = semantic_search(f"{user_text} {issue_terms}", top_k=4)

    result = synthesize_response(
        user_query=user_text, inputs=inputs, analysis=analysis,
        structured_evidence=structured_evidence, semantic_evidence=semantic_evidence,
        missing_fields=[], conversation_history=session.history,
    )

    session.add_turn("assistant", render_result_text(result))
    result["_debug"] = {
        "inputs_used": inputs,
        "issues_detected": analysis["issues"],
        "structured_matches": len(structured_evidence),
        "semantic_matches": len(semantic_evidence),
    }
    return result