"""Notes List, Settings, and About panels — everything that isn't an individual note window."""

import webbrowser
from html.parser import HTMLParser

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .palette import DEFAULT_COLOR, PALETTE


class _PlainTextExtractor(HTMLParser):
    _SKIPPED_TAGS = {"style", "script", "head"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIPPED_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIPPED_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            self.parts.append(data)

    def text(self):
        return "".join(self.parts).strip()


def _snippet(html, length=48):
    parser = _PlainTextExtractor()
    try:
        parser.feed(html or "")
    except Exception:
        return "(empty note)"
    text = " ".join(parser.text().split())
    if not text:
        return "(empty note)"
    if len(text) > length:
        return text[: length - 1] + "…"
    return text


class _NoteRow(QWidget):
    """A clickable list row. Its own background opens the note; the delete
    button is a real child widget, so it gets its own click first."""

    def __init__(self, note_id, on_open):
        super().__init__()
        self._note_id = note_id
        self._on_open = on_open
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_open(self._note_id)
        super().mousePressEvent(event)


class NotesListPanel(QWidget):
    def __init__(self, get_notes, on_open, on_new, on_delete, on_settings):
        super().__init__()
        self._get_notes = get_notes
        self._on_open = on_open
        self._on_new = on_new
        self._on_delete = on_delete
        self._on_settings = on_settings

        self.setWindowTitle("Notes List")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.resize(300, 420)

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        new_btn = QToolButton()
        new_btn.setText("+")
        new_btn.setToolTip("New note")
        new_btn.clicked.connect(self._new_clicked)
        top.addWidget(new_btn)

        title = QLabel("Notes")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        top.addWidget(title, 1, Qt.AlignCenter)

        settings_btn = QToolButton()
        settings_btn.setText("⚙")
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self._on_settings)
        top.addWidget(settings_btn)

        layout.addLayout(top)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(self.list_widget)

    def _new_clicked(self):
        self._on_new()
        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        notes = sorted(
            self._get_notes().values(),
            key=lambda n: n.get("updated_at", 0),
            reverse=True,
        )
        for note in notes:
            note_id = note.get("id")
            row = _NoteRow(note_id, self._open_and_refresh)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(6, 6, 6, 6)

            colors = PALETTE.get(note.get("color"), PALETTE[DEFAULT_COLOR])
            swatch = QLabel()
            swatch.setFixedSize(16, 16)
            swatch.setStyleSheet(f"background-color: {colors['body']}; border-radius: 4px;")
            row_layout.addWidget(swatch)

            text_label = QLabel(_snippet(note.get("html", "")))
            row_layout.addWidget(text_label, 1)

            delete_btn = QToolButton()
            delete_btn.setText("🗑")
            delete_btn.setToolTip("Delete note")
            delete_btn.clicked.connect(lambda checked=False, nid=note_id: self._delete_clicked(nid))
            row_layout.addWidget(delete_btn)

            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, row)

    def _open_and_refresh(self, note_id):
        self._on_open(note_id)
        self.hide()

    def _delete_clicked(self, note_id):
        self._on_delete(note_id)
        self.refresh()


class SettingsDialog(QDialog):
    def __init__(self, settings, on_change, on_about):
        super().__init__()
        self.setWindowTitle("Settings")
        self._settings = dict(settings)
        self._on_change = on_change

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Default color for new notes"))
        self.color_combo = QComboBox()
        for key in PALETTE:
            self.color_combo.addItem(key.capitalize(), key)
        idx = self.color_combo.findData(self._settings.get("default_color", DEFAULT_COLOR))
        if idx >= 0:
            self.color_combo.setCurrentIndex(idx)
        layout.addWidget(self.color_combo)

        self.confirm_checkbox = QCheckBox("Confirm before deleting a note")
        self.confirm_checkbox.setChecked(self._settings.get("confirm_before_delete", True))
        layout.addWidget(self.confirm_checkbox)

        help_btn = QPushButton("Help && Feedback")
        help_btn.clicked.connect(self._open_help)
        layout.addWidget(help_btn)

        about_btn = QPushButton("About")
        about_btn.clicked.connect(on_about)
        layout.addWidget(about_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _open_help(self):
        webbrowser.open("https://github.com/Trozovka/Trozovka-Notes/issues")

    def _accept(self):
        self._on_change(
            {
                "default_color": self.color_combo.currentData(),
                "confirm_before_delete": self.confirm_checkbox.isChecked(),
            }
        )
        self.accept()


class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("About Trozovka Notes")
        self.setFixedWidth(320)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        heart_row = QLabel("💛 🖤 💛")
        heart_row.setAlignment(Qt.AlignCenter)
        heart_row.setFont(QFont("Segoe UI", 18))
        layout.addWidget(heart_row)

        caption = QLabel("It's FOSS, Hell Yeah!")
        caption.setAlignment(Qt.AlignCenter)
        caption.setFont(QFont("Segoe UI", 15, QFont.Bold))
        layout.addWidget(caption)

        body = QLabel(
            "Trozovka Notes is a free, open-source project built by Trozovka — "
            "no ads, no tracking, no account required. Just notes, on your "
            "desktop, the way they should be."
        )
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignCenter)
        layout.addWidget(body)

        link = QLabel(
            '<a href="https://github.com/Trozovka/Trozovka-Notes">'
            "github.com/Trozovka/Trozovka-Notes</a>"
        )
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignCenter)
        layout.addWidget(link)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
