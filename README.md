# Sticky Notes Desktop

A Windows desktop app that mimics Microsoft's Sticky Notes — frameless,
always-on-top notes that float above every other window — with rich text
formatting Microsoft's version doesn't offer: an explicit font-size dropdown
(10–72) alongside Bold and Italic.

Built independently after evaluating existing open-source sticky-note
projects (see [Design notes](#design-notes) below) — none were a clean fit
license- or feature-wise, so this was built from scratch, informed by their
approaches.

## Features

- Multiple independent note windows — frameless, rounded, draggable, resizable
- Always-on-top: notes float above any other Windows application
- Rich text formatting: **Bold**, *Italic*, and a font-size dropdown (10–72)
- Color picker with 7 note colors (yellow, green, pink, purple, blue, gray, charcoal)
- Autosave: content, formatting, position, size, and color persist locally and reload on relaunch
- System tray icon: new note, show all notes, quit

## Tech stack

- **Python 3.12 + PySide6 (Qt)** — chosen over WPF/C# for consistency with
  the rest of this author's projects, and over Tkinter for far easier
  rich-text (`QTextEdit`) and modern styling support.
- No database, no cloud sync, no account — notes are stored in a local
  `notes_data.json` next to the app.

**Why this must run as a native Windows process:** "always on top of any
app" is an OS-level window property. A Linux GUI app (even via WSLg) can
only float above other Linux windows — it cannot overlay native Windows
applications. This app must be run with a **Windows** Python interpreter,
even if the source lives on WSL.

## Setup & run

Requires Python 3.12+ **installed on Windows** (not inside WSL/Linux — see above).

```
git clone https://github.com/Trozovka/sticky-notes-desktop.git
cd sticky-notes-desktop
pip install -r requirements.txt
python main.py
```

The app has no window chrome in the taskbar by design (it's a floating
utility, like the real Sticky Notes) — use the tray icon in the notification
area to create new notes or bring all notes to the front.

## Design notes

Before writing any code, existing open-source sticky-note projects were
searched and evaluated:

| Project | Why it wasn't forked |
|---|---|
| PaperTodo (WPF, 1.4k★) | Feature-rich (font/size/bold/colors) but licensed under PolyForm Noncommercial — not a redistributable open-source license |
| PinnyNotes (WPF, GPL-2.0) | Real always-on-top implementation, but a plain-text power-user tool with no bold/italic/font-size formatting |
| li-zheng-hao/StickyNotes (MIT) | Abandoned since 2023 |
| NoteBot | No LICENSE file at all |
| Playork/StickyNotes | Web app (Vue) — can't achieve OS-level always-on-top |

None were both properly open-source and a close feature match, so this was
built independently. PinnyNotes' `Topmost` window approach informed the
general architecture (not its code).

## License

MIT — see [LICENSE](LICENSE).
