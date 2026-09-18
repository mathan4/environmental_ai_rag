"""
In-process multi-turn conversation memory. One Session per user/land-parcel being
discussed — accumulates structured inputs across turns (so the user doesn't need to
repeat themselves) and keeps a rolling history for context-aware follow-ups.
"""

VALID_LAND_USE = {"monoculture", "polyculture", "agroforestry", "pasture", "fallow"}
VALID_RAINFALL = {"low", "medium", "high"}
VALID_LEVEL = {"low", "medium", "high"}


class Session:
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.inputs: dict = {}
        self.history: list[dict] = []
        # Which required fields were missing the last time we asked a clarifying
        # question — lets a bare one-word reply ("low") be understood in context
        # instead of needing the field name restated ("rainfall is low").
        self.pending_fields: list[str] = []

    def add_turn(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})

    def update_inputs(self, new_fields: dict) -> None:
        """Merges newly extracted/provided fields into the session's known inputs."""
        for k, v in new_fields.items():
            if v not in (None, ""):
                self.inputs[k] = v

    def snapshot(self) -> dict:
        return dict(self.inputs)


_sessions: dict[str, Session] = {}


def get_session(session_id: str = "default") -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session(session_id)
    return _sessions[session_id]