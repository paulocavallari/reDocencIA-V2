from __future__ import annotations

from app.database import Base


def get_import_state() -> dict:
    state = Base.metadata.info.get("curriculum_import_state")
    if state is None:
        state = {
            "status": "idle",
            "total_guides": 0,
            "processed_guides": 0,
            "last_error": None,
            "started_at": None,
            "completed_at": None,
        }
        Base.metadata.info["curriculum_import_state"] = state
    return state


def update_import_state(**changes) -> None:
    state = get_import_state()
    state.update(changes)