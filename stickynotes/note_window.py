"""The individual sticky note window: frameless, always-on-top, rich text."""

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
    closed = Signal(str)
    changed = Signal()
    new_note_requested = Signal()

    _RESIZE_MARGIN = 6

    def __init__(self, note_id=None, data=None, parent=None):
        super().__init__(parent)
        self.note_id = note_id or str(uuid.uuid4())
        data = data or {}
        self._color_key = data.get("color", DEFAULT_COLOR)

        self.setWindowTitle("I ❤ FOSS")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(200, 180)
        self.resize(data.get("width", 260), data.get("height", 260))
        if "x" in data and "y" in data:
            self.move(data["x"], data["y"])

        self._build_ui()
        self._enable_edge_resize()
        self._apply_color(self._color_key)

        if data.get("html"):
            self.body.setHtml(data["html"])
        self._select_font_size(data.get("font_size", DEFAULT_FONT_SIZE))

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
        self.header.setFixedHeight(34)
        layout = QHBoxLayout(self.header)
        layout.setContentsMargins(6, 4, 6, 4)

        self.menu_btn = QToolButton(self.header)
        self.menu_btn.setText("⋮")
        self.menu_btn.setAutoRaise(True)
        self.menu_btn.clicked.connect(self._show_menu)
        layout.addWidget(self.menu_btn)

        self.title_label = QLabel("I ❤ FOSS", self.header)
        title_font = QFont("Segoe UI", 8)
        title_font.setLetterSpacing(QFont.PercentageSpacing, 105)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        layout.addStretch(1)

        self.new_btn = QToolButton(self.header)
        self.new_btn.setText("+")
        self.new_btn.setAutoRaise(True)
        self.new_btn.clicked.connect(self.new_note_requested.emit)
        layout.addWidget(self.new_btn)

        self.close_btn = QToolButton(self.header)
        self.close_btn.setText("✕")
        self.close_btn.setAutoRaise(True)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)

        return self.header

    def _build_toolbar(self):
        self.toolbar = QWidget(self.frame)
        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(6, 2, 6, 6)

        self.bold_btn = QToolButton(self.toolbar)
        self.bold_btn.setText("B")
        self.bold_btn.setCheckable(True)
        bold_font = QFont()
        bold_font.setBold(True)
        self.bold_btn.setFont(bold_font)
        self.bold_btn.setAutoRaise(True)
        self.bold_btn.clicked.connect(self._toggle_bold)
        layout.addWidget(self.bold_btn)

        self.italic_btn = QToolButton(self.toolbar)
        self.italic_btn.setText("I")
        self.italic_btn.setCheckable(True)
        italic_font = QFont()
        italic_font.setItalic(True)
        self.italic_btn.setFont(italic_font)
        self.italic_btn.setAutoRaise(True)
        self.italic_btn.clicked.connect(self._toggle_italic)
        layout.addWidget(self.italic_btn)

        layout.addSpacing(8)

        self.size_combo = QComboBox(self.toolbar)
        for size in FONT_SIZES:
            self.size_combo.addItem(str(size), size)
        self.size_combo.setFixedWidth(60)
        self.size_combo.currentIndexChanged.connect(self._apply_font_size)
        layout.addWidget(self.size_combo)

        layout.addStretch(1)

        return self.toolbar

    # ---------- edge/corner resize ----------
    def _enable_edge_resize(self):
        self.setMouseTracking(True)
        for widget in self.findChildren(QWidget):
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

    def _show_menu(self):
        menu = QMenu(self)
        color_menu = menu.addMenu("Color")
        for key in PALETTE:
            action = QAction(key.capitalize(), self)
            action.triggered.connect(lambda checked=False, k=key: self._apply_color(k, persist=True))
            color_menu.addAction(action)
        menu.addSeparator()
        delete_action = QAction("Delete Note", self)
        delete_action.triggered.connect(self.close)
        menu.addAction(delete_action)
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    # ---------- color ----------
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
        for btn in (self.menu_btn, self.new_btn, self.close_btn, self.bold_btn, self.italic_btn):
            btn.setStyleSheet(f"color: {colors['text']}; border: none;")
        self.title_label.setStyleSheet(f"color: {colors['text']}; background: transparent;")
        self.body.setStyleSheet(f"background: transparent; border: none; color: {colors['text']};")
        if persist:
            self.request_save()

    # ---------- formatting ----------
    def _toggle_bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if self.bold_btn.isChecked() else QFont.Normal)
        self.body.mergeCurrentCharFormat(fmt)
        self.body.setFocus()

    def _toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_btn.isChecked())
        self.body.mergeCurrentCharFormat(fmt)
        self.body.setFocus()

    def _apply_font_size(self):
        size = self.size_combo.currentData()
        if size is None:
            return
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self.body.mergeCurrentCharFormat(fmt)
        self.body.setFocus()

    def _sync_toolbar_to_cursor(self):
        fmt = self.body.currentCharFormat()
        self.bold_btn.blockSignals(True)
        self.italic_btn.blockSignals(True)
        self.bold_btn.setChecked(fmt.fontWeight() == QFont.Bold)
        self.italic_btn.setChecked(fmt.fontItalic())
        self.bold_btn.blockSignals(False)
        self.italic_btn.blockSignals(False)
        self._select_font_size(int(fmt.fontPointSize()) or DEFAULT_FONT_SIZE)

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
            "font_size": self.size_combo.currentData() or DEFAULT_FONT_SIZE,
        }

    def closeEvent(self, event):
        self.closed.emit(self.note_id)
        super().closeEvent(event)
