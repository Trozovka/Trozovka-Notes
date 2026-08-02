"""The individual sticky note window: frameless, always-on-top, rich text."""

import time
import uuid

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QAction, QFont, QTextCharFormat
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .palette import DEFAULT_COLOR, PALETTE

FONT_SIZES = [10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48, 56, 64, 72]
DEFAULT_FONT_SIZE = 12
DEFAULT_FONT_FAMILY = "Calibri"


class _Header(QWidget):
    """Drag handle strip. Owns its own mouse events so dragging never leaks
    into the text body below it."""

    def __init__(self, note_window, parent=None):
        super().__init__(parent)
        self._note_window = note_window
        self._drag_offset = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._note_window.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self._note_window.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_offset is not None:
            self._drag_offset = None
            self._note_window.request_save()
        super().mouseReleaseEvent(event)


class NoteWindow(QWidget):
    # Emitted when the window is closed (X, Alt+F4, etc.) — the note's data
    # is NOT deleted, just no longer shown. See delete_requested for that.
    window_closed = Signal(str)
    delete_requested = Signal(str)
    notes_list_requested = Signal()
    changed = Signal()
    new_note_requested = Signal()

    _RESIZE_MARGIN = 6

    def __init__(self, note_id=None, data=None, parent=None):
        super().__init__(parent)
        self.note_id = note_id or str(uuid.uuid4())
        data = data or {}
        self._color_key = data.get("color", DEFAULT_COLOR)
        self._preferred_font_size = data.get("font_size", DEFAULT_FONT_SIZE)
        self._always_on_top = data.get("always_on_top", True)

        self.setWindowTitle("I ❤ FOSS")
        self.setWindowFlags(self._window_flags())
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setMinimumSize(200, 180)
        self.resize(data.get("width", 260), data.get("height", 260))
        if "x" in data and "y" in data:
            self.move(data["x"], data["y"])

        self._build_ui()
        self._enable_edge_resize()
        self._apply_color(self._color_key)

        if data.get("html"):
            self.body.setHtml(data["html"])
        self._select_font_size(self._preferred_font_size)

        self.body.textChanged.connect(self.request_save)
        self.body.cursorPositionChanged.connect(self._sync_toolbar_to_cursor)

    # ---------- UI construction ----------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.frame = QFrame(self)
        self.frame.setObjectName("noteFrame")
        outer.addWidget(self.frame)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(Qt.black)
        self.frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        frame_layout.addWidget(self._build_header())

        self.body = QTextEdit(self.frame)
        self.body.setFrameShape(QFrame.NoFrame)
        self.body.setAcceptRichText(True)
        default_font = QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE)
        self.body.setFont(default_font)
        frame_layout.addWidget(self.body, 1)

        frame_layout.addWidget(self._build_toolbar())

    def _build_header(self):
        self.header = _Header(self, self.frame)
        self.header.setFixedHeight(40)
        layout = QHBoxLayout(self.header)
        layout.setContentsMargins(10, 4, 6, 4)

        self.title_label = QLabel("I ❤ FOSS", self.header)
        title_font = QFont("Segoe UI", 14)
        title_font.setLetterSpacing(QFont.PercentageSpacing, 105)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        header_icon_font = QFont("Segoe UI", 15)

        self.pin_btn = QToolButton(self.header)
        self.pin_btn.setText("📌")
        self.pin_btn.setFont(header_icon_font)
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(self._always_on_top)
        self.pin_btn.setToolTip("Always on top of other windows (click to turn off)")
        layout.addWidget(self.pin_btn)
        self.pin_btn.clicked.connect(self._toggle_pin)

        layout.addStretch(1)

        self.new_btn = QToolButton(self.header)
        self.new_btn.setText("+")
        self.new_btn.setFont(header_icon_font)
        self.new_btn.setToolTip("New note")
        layout.addWidget(self.new_btn)
        self.new_btn.clicked.connect(self.new_note_requested.emit)

        self.notes_list_btn = QToolButton(self.header)
        self.notes_list_btn.setText("⋯")
        self.notes_list_btn.setFont(header_icon_font)
        self.notes_list_btn.setToolTip("Notes list")
        layout.addWidget(self.notes_list_btn)
        self.notes_list_btn.clicked.connect(self.notes_list_requested.emit)

        self.close_btn = QToolButton(self.header)
        self.close_btn.setText("✕")
        self.close_btn.setFont(header_icon_font)
        self.close_btn.setToolTip("Close (the note is kept — right-click for delete)")
        layout.addWidget(self.close_btn)
        self.close_btn.clicked.connect(self.close)

        return self.header

    def _build_toolbar(self):
        self.toolbar = QWidget(self.frame)
        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(6, 2, 6, 8)

        self.bold_btn = QToolButton(self.toolbar)
        self.bold_btn.setText("B")
        self.bold_btn.setCheckable(True)
        bold_font = QFont()
        bold_font.setBold(True)
        self.bold_btn.setFont(bold_font)
        self.bold_btn.clicked.connect(self._toggle_bold)
        layout.addWidget(self.bold_btn)

        self.italic_btn = QToolButton(self.toolbar)
        self.italic_btn.setText("I")
        self.italic_btn.setCheckable(True)
        italic_font = QFont()
        italic_font.setItalic(True)
        self.italic_btn.setFont(italic_font)
        self.italic_btn.clicked.connect(self._toggle_italic)
        layout.addWidget(self.italic_btn)

        layout.addSpacing(8)

        self.size_combo = QComboBox(self.toolbar)
        self.size_combo.setFont(QFont("Segoe UI", 10))
        for size in FONT_SIZES:
            self.size_combo.addItem(str(size), size)
        self.size_combo.setFixedWidth(72)
        self.size_combo.setMinimumHeight(26)
        self.size_combo.currentIndexChanged.connect(self._apply_font_size)
        layout.addWidget(self.size_combo)

        layout.addStretch(1)

        return self.toolbar

    # ---------- always-on-top toggle ----------
    def _window_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self._always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        return flags

    def _toggle_pin(self):
        self._always_on_top = self.pin_btn.isChecked()
        pos, size = self.pos(), self.size()
        self.setWindowFlags(self._window_flags())
        self.resize(size)
        self.move(pos)
        self.show()
        self.request_save()

    # ---------- edge/corner resize ----------
    def _enable_edge_resize(self):
        self.setMouseTracking(True)
        for widget in self.findChildren(QWidget):
            # Buttons and the combo box handle their own clicks; letting the
            # resize hit-test claim their edge pixels made them need two
            # clicks to register (first click consumed as a resize attempt).
            if isinstance(widget, (QToolButton, QComboBox)):
                continue
            widget.setMouseTracking(True)
            widget.installEventFilter(self)

    def _edge_at(self, global_pos):
        geo = self.geometry()
        m = self._RESIZE_MARGIN
        horizontal = None
        if global_pos.x() <= geo.left() + m:
            horizontal = Qt.LeftEdge
        elif global_pos.x() >= geo.right() - m:
            horizontal = Qt.RightEdge
        vertical = None
        if global_pos.y() <= geo.top() + m:
            vertical = Qt.TopEdge
        elif global_pos.y() >= geo.bottom() - m:
            vertical = Qt.BottomEdge
        if horizontal and vertical:
            return horizontal | vertical
        return horizontal or vertical

    @staticmethod
    def _cursor_for_edges(edges):
        if not edges:
            return None
        top = bool(edges & Qt.TopEdge)
        bottom = bool(edges & Qt.BottomEdge)
        left = bool(edges & Qt.LeftEdge)
        right = bool(edges & Qt.RightEdge)
        if (top and left) or (bottom and right):
            return Qt.SizeFDiagCursor
        if (top and right) or (bottom and left):
            return Qt.SizeBDiagCursor
        if top or bottom:
            return Qt.SizeVerCursor
        return Qt.SizeHorCursor

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseMove:
            edges = self._edge_at(event.globalPosition().toPoint())
            cursor = self._cursor_for_edges(edges)
            if cursor is not None:
                obj.setCursor(cursor)
            else:
                obj.unsetCursor()
        elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            edges = self._edge_at(event.globalPosition().toPoint())
            if edges:
                window = self.windowHandle()
                if window is not None and window.startSystemResize(edges):
                    return True
        return super().eventFilter(obj, event)

    # ---------- per-note color / delete (right-click) ----------
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        color_menu = menu.addMenu("Color")
        for key in PALETTE:
            action = QAction(key.capitalize(), self)
            action.triggered.connect(lambda checked=False, k=key: self._apply_color(k, persist=True))
            color_menu.addAction(action)
        menu.addSeparator()
        delete_action = QAction("Delete Note", self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.note_id))
        menu.addAction(delete_action)
        menu.exec(event.globalPos())

    # ---------- color ----------
    @staticmethod
    def _tint(hex_color, alpha):
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"

    def _apply_color(self, key, persist=False):
        self._color_key = key
        colors = PALETTE.get(key, PALETTE[DEFAULT_COLOR])
        self.frame.setStyleSheet(
            f"#noteFrame {{ background-color: {colors['body']}; border-radius: 10px; }}"
        )
        self.header.setStyleSheet(
            f"background-color: {colors['header']};"
            "border-top-left-radius: 10px; border-top-right-radius: 10px;"
        )

        resting = self._tint(colors["text"], 20)
        tint = self._tint(colors["text"], 40)
        tint_hover = self._tint(colors["text"], 60)
        tint_pressed = self._tint(colors["text"], 85)
        button_qss = (
            f"QToolButton {{ color: {colors['text']}; border: none; border-radius: 5px;"
            f" padding: 3px 7px; background-color: {resting}; }}"
            f"QToolButton:hover {{ background-color: {tint}; }}"
            f"QToolButton:pressed {{ background-color: {tint_pressed}; }}"
            f"QToolButton:checked {{ background-color: {tint_hover}; }}"
        )
        for btn in (self.pin_btn, self.new_btn, self.notes_list_btn, self.close_btn, self.bold_btn, self.italic_btn):
            btn.setStyleSheet(button_qss)

        self.title_label.setStyleSheet(f"color: {colors['text']}; background: transparent;")
        self.body.setStyleSheet(f"background: transparent; border: none; color: {colors['text']};")

        self.size_combo.setStyleSheet(
            f"QComboBox {{ color: {colors['text']}; background-color: {tint}; border: none;"
            f" border-radius: 5px; padding: 2px 8px; }}"
            f"QComboBox:hover {{ background-color: {tint_hover}; }}"
            f"QComboBox QAbstractItemView {{ background-color: white; color: #2A2A2A;"
            f" selection-background-color: {colors['header']}; outline: none; }}"
            f"QComboBox QAbstractItemView::item {{ padding: 6px 10px; min-height: 22px; }}"
        )

        if persist:
            self.request_save()

    # ---------- formatting ----------
    def _toggle_bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if self.bold_btn.isChecked() else QFont.Normal)
        self.body.mergeCurrentCharFormat(fmt)
        self.body.setFocus()
        # mergeCurrentCharFormat with no selection doesn't fire textChanged,
        # so without this, toggling bold with nothing selected wouldn't save.
        self.request_save()

    def _toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_btn.isChecked())
        self.body.mergeCurrentCharFormat(fmt)
        self.body.setFocus()
        self.request_save()

    def _apply_font_size(self):
        size = self.size_combo.currentData()
        if size is None:
            return
        self._preferred_font_size = size
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self.body.mergeCurrentCharFormat(fmt)
        self.body.setFocus()
        self.request_save()

    def _sync_toolbar_to_cursor(self):
        fmt = self.body.currentCharFormat()
        self.bold_btn.blockSignals(True)
        self.italic_btn.blockSignals(True)
        self.bold_btn.setChecked(fmt.fontWeight() == QFont.Bold)
        self.italic_btn.setChecked(fmt.fontItalic())
        self.bold_btn.blockSignals(False)
        self.italic_btn.blockSignals(False)

        # An unset point size (0) means "inherit" — without this, landing on
        # one (e.g. right after deleting text) made the size dropdown, and
        # subsequently typed text, silently drop back to the base 12pt
        # instead of whatever size the user had actually chosen.
        size = int(fmt.fontPointSize())
        if size <= 0:
            size = self._preferred_font_size
            fix_fmt = QTextCharFormat()
            fix_fmt.setFontPointSize(size)
            self.body.mergeCurrentCharFormat(fix_fmt)
        self._select_font_size(size)

    def _select_font_size(self, size):
        idx = self.size_combo.findData(size)
        self.size_combo.blockSignals(True)
        self.size_combo.setCurrentIndex(idx if idx >= 0 else self.size_combo.findData(DEFAULT_FONT_SIZE))
        self.size_combo.blockSignals(False)

    # ---------- persistence ----------
    def request_save(self):
        self.changed.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.request_save()

    def to_dict(self):
        return {
            "id": self.note_id,
            "html": self.body.toHtml(),
            "color": self._color_key,
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "font_size": self._preferred_font_size,
            "always_on_top": self._always_on_top,
            "updated_at": time.time(),
        }

    def closeEvent(self, event):
        self.window_closed.emit(self.note_id)
        super().closeEvent(event)
