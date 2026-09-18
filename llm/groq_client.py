"""
Groq wrapper for the final synthesis step. Deliberately constrained: the model is
given the structured interventions + semantic passages + linked issues as its ONLY
source of numbers and citations, and instructed not to introduce new ones. This is
what keeps output evidence-backed rather than plausible-sounding LLM invention.
"""
import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = None

OUTPUT_SCHEMA_EXAMPLE = {
    "clarifying_question": None,
    "recommendations": [
        {
            "action": "What to do, specific and non-generic",
            "why": "Scientific mechanism, in plain language",
            "impacted_metrics": ["soil_organic_carbon", "pollinator_diversity"],
            "estimated_effect": "e.g. 15-25% increase over the stated time horizon",
            "time_horizon": "short | medium | long",
            "time_horizon_detail": "e.g. 2-3 years",
            "confidence": "high | medium | low",
            "source": "e.g. FAO; IPCC land-use assessments",
        }
    ],
    "variable_links": ["soil_organic_carbon <-> pollinator_diversity", "..."],
}


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Copy .env.example to .env and fill it in.")
        _client = Groq(api_key=api_key)
    return _client


def synthesize_response(user_query: str, inputs: dict, analysis: dict,
                         structured_evidence: list[dict], semantic_evidence: list[dict],
                         missing_fields: list[str], conversation_history: list[dict]) -> dict:
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    if missing_fields:
        # Not enough info to reason responsibly — ask, don't guess.
        system_prompt = (
            "You are an environmental scientist assistant. The user has not yet provided "
            "enough information to give a grounded recommendation. Ask ONE concise "
            "clarifying question requesting the missing fields, in plain language "
            "(don't expose internal field names verbatim). "
            "Respond with ONLY a JSON object: {\"clarifying_question\": \"...\", "
            "\"recommendations\": [], \"variable_links\": []}"
        )
        user_prompt = f"User said: {user_query}\nMissing fields (internal names): {missing_fields}"
    else:
        # Increased from a 6-turn window: rendered turns are now short, clean text
        # (see core/formatting.py) rather than raw Python list reprs, so a larger
        # window costs little and gives the model more real conversational grounding.
        history_block = "\n\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in conversation_history[-10:]
        ) or "No prior turns — this is the first exchange."

        structured_block = json.dumps(structured_evidence, indent=2) if structured_evidence else "None matched."
        semantic_block = "\n\n".join(
            f"[{s['source']}{', p.' + str(s['page']) if s.get('page') else ''}]: {s['text']}"
            for s in semantic_evidence
        ) or "None retrieved."
        issues_block = "\n".join(f"- {i['issue']}: {i['detail']}" for i in analysis["issues"]) or "None detected."
        links_block = "\n".join(f"- {l}" for l in analysis["linked_variables"]) or "None."

        system_prompt = (
            "You are an environmental scientist assistant producing evidence-backed "
            "biodiversity recommendations, in an ONGOING multi-turn conversation with a "
            "real user. You are given: the full conversation history so far, detected "
            "cross-variable issues, structured intervention data (with real effect "
            "ranges, time horizons, and sources — use these numbers and sources, do not "
            "invent your own), and supporting scientific-reasoning passages.\n\n"
            "How to use the conversation history (read it before answering):\n"
            "- If the current user message provides NEW environmental data (a number, a "
            "land-use type, a rainfall level, etc.), treat this as an update and generate "
            "fresh recommendations grounded in the full updated picture.\n"
            "- If the current user message is FEEDBACK or a REFINEMENT REQUEST on what "
            "you already said (e.g. 'bad', 'be more specific', 'be conversational', "
            "'what crops exactly') rather than new data, do NOT just restate your previous "
            "recommendations in different words. Look at what you already told the user "
            "(the ASSISTANT turns in the history) and give something that is genuinely "
            "more useful given that specific feedback — more concrete, more specific, "
            "less repetitive, or in a different tone as asked — while staying grounded "
            "in the same evidence.\n"
            "- Never contradict or silently drop a recommendation you already gave unless "
            "the user's new input changes the underlying data.\n\n"
            "Other rules:\n"
            "- Every recommendation must combine at least 2 of the detected issues/linked "
            "variables in its reasoning, not just one.\n"
            "- Use ONLY the numeric ranges and sources given in the structured data. If no "
            "structured data matches, omit estimated_effect/source rather than inventing them.\n"
            "- Recommendations must be specific and non-obvious (never say things like "
            "'use sustainable practices').\n"
            "- Respond with ONLY a JSON object matching exactly this shape:\n"
            f"{json.dumps(OUTPUT_SCHEMA_EXAMPLE, indent=2)}"
        )
        user_prompt = f"""Conversation so far (read this — the current message may be feedback on it, not new data):
{history_block}

Current user message: {user_query}

Current known inputs (accumulated across the whole conversation): {json.dumps(inputs)}

Detected cross-variable issues:
{issues_block}

Linked variables:
{links_block}

Structured intervention evidence (numbers/sources to use):
{structured_block}

Supporting scientific reasoning passages:
{semantic_block}

Produce the JSON response now.
"""

    resp = _get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)