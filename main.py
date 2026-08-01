import sys

from PySide6.QtWidgets import QApplication

from stickynotes.note_manager import NoteManager


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Trozovka Notes")
    app.setQuitOnLastWindowClosed(False)  # keep running in the tray with 0 notes open

    manager = NoteManager(app)
    manager.load_all()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
