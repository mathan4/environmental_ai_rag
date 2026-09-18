"""
Usage:
    python main.py chat                  # interactive multi-turn conversation
    python main.py example               # runs the spec's example use case once
    python main.py json <path-to-json>    # single-shot structured JSON input
"""
import sys
import json
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from core.engine import handle_message
from core.formatting import render_result_text


def print_result(result: dict):
    if result.get("clarifying_question"):
        print(f"\nSystem: {result['clarifying_question']}\n")
        return
    if result.get("reply"):
        # Conversational prose -- print plainly, like a normal chat reply, not
        # boxed as if it were a structured recommendation report.
        print(f"\nSystem: {result['reply']}\n")
        return
    print("\n" + "=" * 60)
    print(render_result_text(result))
    print("=" * 60)


def chat():
    print("Eco Advisor — describe your land/ecosystem situation (type 'quit' to exit).\n")
    session_id = "cli-session"
    while True:
        user_text = input("You: ").strip()
        if user_text.lower() in ("quit", "exit"):
            break
        result = handle_message(user_text, session_id=session_id)
        print_result(result)


def example():
    """Runs the exact example from the spec: SOC 0.3%, low rainfall, monoculture wheat, semi-arid."""
    session_id = "example-session"
    text = (
        "My land has soil organic carbon of 0.3%, rainfall is low, "
        "we grow monoculture wheat, and it's a semi-arid region. "
        "Biodiversity seems to be declining."
    )
    print(f"You: {text}\n")
    result = handle_message(text, session_id=session_id)
    print_result(result)


def from_json(path: str):
    with open(path) as f:
        data = json.load(f)
    text = data.pop("query", "Please analyze my land based on the provided data.")
    result = handle_message(text, session_id="json-session", structured_input=data)
    print_result(result)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "chat":
        chat()
    elif cmd == "example":
        example()
    elif cmd == "json" and len(sys.argv) > 2:
        from_json(sys.argv[2])
    else:
        print(__doc__)