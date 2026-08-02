"""Local JSON persistence for notes and app settings — no cloud sync, no account, all on-disk."""

import json
import os
import sys
from pathlib import Path

DEFAULT_SETTINGS = {
    "default_color": "yellow",
    "confirm_before_delete": True,
}


def _default_data_path() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller onefile: __file__ points into a temp extraction dir
        # that's wiped after each run, so notes must live somewhere durable.
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Trozovka Notes"
        base.mkdir(parents=True, exist_ok=True)
        return base / "notes_data.json"
    return Path(__file__).resolve().parent.parent / "notes_data.json"


DATA_FILE = _default_data_path()


class NoteStore:
    """Persists every note ever created (`notes`), which one was last active,
    and app-wide settings — as one JSON document, since they're always
    read/written together."""

    def __init__(self, path: Path = DATA_FILE):
        self.path = path

    def load(self):
        if not self.path.is_file():
            return {"notes": [], "last_active_id": None, "settings": dict(DEFAULT_SETTINGS)}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"notes": [], "last_active_id": None, "settings": dict(DEFAULT_SETTINGS)}

        if isinstance(raw, list):
            # Pre-existing format: a bare list of notes, no settings/last-active yet.
            return {"notes": raw, "last_active_id": None, "settings": dict(DEFAULT_SETTINGS)}

        settings = dict(DEFAULT_SETTINGS)
        settings.update(raw.get("settings") or {})
        return {
            "notes": raw.get("notes", []),
            "last_active_id": raw.get("last_active_id"),
            "settings": settings,
        }

    def save(self, notes, last_active_id, settings):
        payload = {
            "notes": notes,
            "last_active_id": last_active_id,
            "settings": settings,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
