"""Owns every note (open or not), the tray icon, and debounced autosave.

Persistence model: `all_notes` is the full, durable store — every note ever
created, whether or not it currently has an open window. `notes` tracks only
the windows currently shown. Closing a window removes it from `notes` but
never touches `all_notes`, so a note's content survives closing it and
surviving a restart; only an explicit delete removes it from `all_notes`.
"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

from .note_window import NoteWindow
from .palette import DEFAULT_COLOR
from .panels import AboutDialog, NotesListPanel, SettingsDialog
from .storage import NoteStore

SAVE_DEBOUNCE_MS = 600


def _tray_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#FFF6A9"))
    painter.setPen(QColor("#F5E27A"))
    painter.drawRoundedRect(4, 4, 56, 56, 10, 10)
    painter.end()
    return QIcon(pixmap)


class NoteManager:
    def __init__(self, app):
        self.app = app
        self.store = NoteStore()
        self.notes = {}  # note_id -> open NoteWindow
        self.all_notes = {}  # note_id -> persisted note dict (open or closed)
        self.settings = {}
        self.last_active_id = None
        self._notes_list = None

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DEBOUNCE_MS)
        self._save_timer.timeout.connect(self._save_all)

        self._settings_dialog = None
        self._about_dialog = None

        self._build_tray()

    def _build_tray(self):
        self.tray = QSystemTrayIcon(_tray_icon())
        self.tray.setToolTip("Trozovka Notes")

        menu = QMenu()
        new_action = QAction("New Note", menu)
        new_action.triggered.connect(self.create_note)
        menu.addAction(new_action)

        list_action = QAction("Notes List", menu)
        list_action.triggered.connect(self.show_notes_list)
        menu.addAction(list_action)

        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    # ---------- startup ----------
    def load_all(self):
        stored = self.store.load()
        self.settings = stored["settings"]
        self.all_notes = {n["id"]: n for n in stored["notes"] if "id" in n}
        self.last_active_id = stored["last_active_id"]

        open_id = self._pick_note_to_open()
        if open_id is None:
            self.create_note()
            return
        self._add_note(note_id=open_id, data=self.all_notes[open_id])

    def _pick_note_to_open(self):
        if self.last_active_id and self.last_active_id in self.all_notes:
            return self.last_active_id
        if not self.all_notes:
            return None
        return max(self.all_notes.values(), key=lambda n: n.get("updated_at", 0))["id"]

    # ---------- creating / opening ----------
    def create_note(self):
        color = self.settings.get("default_color", DEFAULT_COLOR)
        data = {"color": color}
        # Without an explicit position, Qt places every new note at the same
        # default spot — cascade from whatever's currently open so a new
        # note doesn't spawn invisibly stacked under an existing one.
        origin = self.notes.get(self.last_active_id) or next(iter(self.notes.values()), None)
        if origin is not None:
            data["x"] = origin.x() + 28
            data["y"] = origin.y() + 28
        self._add_note(data=data)

    def open_note(self, note_id):
        existing = self.notes.get(note_id)
        if existing is not None:
            existing.show()
            existing.raise_()
            existing.activateWindow()
            return
        data = self.all_notes.get(note_id)
        if data is not None:
            self._add_note(note_id=note_id, data=data)

    def _add_note(self, note_id=None, data=None):
        note = NoteWindow(note_id=note_id, data=data)
        note.window_closed.connect(self._on_window_closed)
        note.changed.connect(lambda note_id=note.note_id: self._on_note_changed(note_id))
        note.new_note_requested.connect(self.create_note)
        note.notes_list_requested.connect(self.show_notes_list)
        note.delete_requested.connect(self.delete_note)
        self.notes[note.note_id] = note
        self.all_notes[note.note_id] = note.to_dict()
        self.last_active_id = note.note_id
        note.show()
        return note

    # ---------- closing / deleting ----------
    def _on_window_closed(self, note_id):
        self.notes.pop(note_id, None)
        self._schedule_save()

    def delete_note(self, note_id):
        if self.settings.get("confirm_before_delete", True):
            parent = self.notes.get(note_id)
            reply = QMessageBox.question(
                parent,
                "Delete note?",
                "This note will be permanently deleted. This can't be undone.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.all_notes.pop(note_id, None)
        widget = self.notes.pop(note_id, None)
        if widget is not None:
            widget.close()
        if self.last_active_id == note_id:
            self.last_active_id = next(iter(self.all_notes), None)
        self._schedule_save()

    # ---------- autosave ----------
    def _on_note_changed(self, note_id):
        note = self.notes.get(note_id)
        if note is None:
            return
        self.all_notes[note_id] = note.to_dict()
        self.last_active_id = note_id
        self._schedule_save()

    def _schedule_save(self):
        self._save_timer.start()

    def _save_all(self):
        self.store.save(list(self.all_notes.values()), self.last_active_id, self.settings)

    # ---------- notes list / settings / about ----------
    def show_notes_list(self):
        if self._notes_list is None:
            self._notes_list = NotesListPanel(
                get_notes=lambda: self.all_notes,
                on_open=self.open_note,
                on_new=self.create_note,
                on_delete=self.delete_note,
                on_settings=self.show_settings,
            )
        self._notes_list.refresh()
        self._notes_list.show()
        self._notes_list.raise_()
        self._notes_list.activateWindow()

    def show_settings(self):
        # Deliberately non-modal (.show(), not .exec()): a modal dialog can
        # end up rendered behind one of the several always-on-top note
        # windows, invisible but still blocking input to the entire app with
        # no way to dismiss it short of killing the process. Non-modal means
        # that failure mode can't lock anything up even if it recurs.
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(
                self.settings, on_change=self._on_settings_changed, on_about=self.show_about, parent=self._notes_list
            )
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def _on_settings_changed(self, settings):
        self.settings.update(settings)
        self._schedule_save()

    def show_about(self):
        if self._about_dialog is None:
            self._about_dialog = AboutDialog(parent=self._notes_list)
        self._about_dialog.show()
        self._about_dialog.raise_()
        self._about_dialog.activateWindow()

    # ---------- tray ----------
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_notes_list()

    def quit(self):
        self._save_all()
        self.app.quit()
