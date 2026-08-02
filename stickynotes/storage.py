"""Local JSON persistence for notes — no cloud sync, no account, all on-disk."""

import json
import os
import sys
from pathlib import Path


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
    def __init__(self, path: Path = DATA_FILE):
        self.path = path

    def load(self):
        if not self.path.is_file():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def save(self, notes):
        self.path.write_text(json.dumps(notes, indent=2), encoding="utf-8")
