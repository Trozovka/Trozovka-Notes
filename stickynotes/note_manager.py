"""Owns the set of open notes, the tray icon, and debounced autosave."""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .note_window import NoteWindow
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
        self.notes = {}

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DEBOUNCE_MS)
        self._save_timer.timeout.connect(self._save_all)

        self._build_tray()

    def _build_tray(self):
        self.tray = QSystemTrayIcon(_tray_icon())
        self.tray.setToolTip("Sticky Notes")

        menu = QMenu()
        new_action = QAction("New Note", menu)
        new_action.triggered.connect(self.create_note)
        menu.addAction(new_action)

        show_action = QAction("Show All Notes", menu)
        show_action.triggered.connect(self.show_all)
        menu.addAction(show_action)

        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def load_all(self):
        saved = self.store.load()
        if not saved:
            self.create_note()
            return
        for data in saved:
            self._add_note(note_id=data.get("id"), data=data)

    def create_note(self):
        self._add_note()

    def _add_note(self, note_id=None, data=None):
        note = NoteWindow(note_id=note_id, data=data)
        note.closed.connect(self._on_note_closed)
        note.changed.connect(self._schedule_save)
        note.new_note_requested.connect(self.create_note)
        self.notes[note.note_id] = note
        note.show()

    def _on_note_closed(self, note_id):
        self.notes.pop(note_id, None)
        self._schedule_save()

    def _schedule_save(self):
        self._save_timer.start()

    def _save_all(self):
        self.store.save([note.to_dict() for note in self.notes.values()])

    def show_all(self):
        if not self.notes:
            self.create_note()
            return
        for note in self.notes.values():
            note.show()
            note.raise_()
            note.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_all()

    def quit(self):
        self._save_all()
        self.app.quit()
