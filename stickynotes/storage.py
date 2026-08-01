"""Local JSON persistence for notes — no cloud sync, no account, all on-disk."""

import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "notes_data.json"


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
