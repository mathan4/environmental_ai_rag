"""
End-to-end orchestration:
1. Extract/merge structured fields from the user's text (or accept structured JSON directly)
2. Run multi-metric reasoning on whatever inputs are known so far (works fine even
   with partial/no data -- analyze() is null-safe)
3. Retrieve structured interventions + semantic passages based on whatever was detected
4. Synthesize the response via Groq -- the LLM itself decides, per turn, whether this
   is a general question it can answer directly (`reply`), a site-specific analysis
   request that's missing required data (`clarifying_question`), or a request for a
   fresh recommendation set (`recommendations`). Required-field completeness is passed
   as INFORMATION, not used as a hard Python-level gate -- a general conceptual question
   ("should I use GM seeds?", "what is agroforestry?") should get answered on its own
   terms, not blocked until soil/rainfall/land-use are all on file.
5. Update conversation memory
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

    # analyze() is null-safe (checks `x is not None` before every threshold comparison),
    # so this works fine with zero, partial, or complete inputs -- no separate code path
    # needed for "not enough data yet".
    analysis = analyze(inputs)

    detected_issue_tags = [i["issue"] for i in analysis["issues"]]
    structured_evidence = get_structured_interventions(detected_issue_tags) if detected_issue_tags else []

    # Query the knowledge base with whatever we have -- the user's own message always
    # contributes, issue terms add specificity once any data is known.
    issue_terms = " ".join(i["issue"].replace("_", " ") for i in analysis["issues"])
    semantic_query = f"{user_text} {issue_terms}".strip()
    semantic_evidence = semantic_search(semantic_query, top_k=4)

    result = synthesize_response(
        user_query=user_text, inputs=inputs, analysis=analysis,
        structured_evidence=structured_evidence, semantic_evidence=semantic_evidence,
        missing_fields=missing, conversation_history=session.history,
    )

    # pending_fields only matters for the bare-answer context fallback (see
    # conversation/input_parser.py) -- set it when the model actually asked a
    # clarifying question this turn, clear it otherwise.
    session.pending_fields = missing if result.get("clarifying_question") else []

    session.add_turn("assistant", render_result_text(result))
    result["_debug"] = {
        "inputs_used": inputs,
        "missing_required_fields": missing,
        "issues_detected": analysis["issues"],
        "structured_matches": len(structured_evidence),
        "semantic_matches": len(semantic_evidence),
    }
    return result
