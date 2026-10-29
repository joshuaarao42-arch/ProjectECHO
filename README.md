# Project ECHO

Project ECHO is an offline-first digital time capsule for Windows. Write a letter, journal entry, milestone, memory, or goal and choose when you want to open it. Your data stays on your computer; the app does not use a cloud service or connect to a server.

> **Author:** Joshua C. Arao, first-year Computer Science student

## Features

- Create capsules with a title, category, tags, and an unlock date.
- Browse and search your capsules by title, tag, category, status, and date.
- View a dashboard, chronological timeline, and writing statistics and reflections.
- Protect capsule titles, tags, and text with AES-256-GCM encryption and a master password.
- Lock the app automatically after a configurable period of inactivity.
- Export and restore encrypted backups.
- Choose a high-contrast blue-violet theme in light, dark, or system appearance mode. Light mode is the default.
- Optionally add or remove fictional demonstration capsules from Settings.

## Requirements

- Windows
- Python 3.10 or newer
- The Python `py` launcher on your PATH (used by the setup scripts)

The app uses Python, CustomTkinter, and SQLite. Dependencies are listed in [`requirements.txt`](requirements.txt).

## Install and run

### Quick start

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/). Make sure the Python launcher is installed.
2. Download or clone this repository.
3. Double-click `run_echo.bat`. On first launch, it creates a local `.venv` and installs the required packages.

### Run from a terminal

Open Command Prompt in the project folder and run:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

The first time you open the app, create a master password for your vault. **The password cannot be recovered if you forget it.**

## Run tests

With dependencies installed, run either:

```bat
run_tests.bat
```

or:

```bat
python -m unittest discover -s tests -t . -v
```

The tests cover database behavior, validation and dates, capsule access rules, encryption, authentication, and backup validation. They do not require a display.

## Data, privacy, and security

- By default, application data is stored in `%LOCALAPPDATA%\ProjectECHO`, including the SQLite database and application log.
- Set the `ECHO_DATA_DIR` environment variable before launching the app to use a different data directory.
- Capsule titles, tags, and text are encrypted at rest using AES-256-GCM. A key derived from your master password with scrypt protects the encryption key.
- Category, dates, and favorite, archive, and opened status are stored unencrypted so the app can sort and filter capsules.
- The app does not write capsule titles or text to its logs or notifications.
- Unlock dates are enforced by the application, not by cryptography. Someone who modifies the software or changes the system clock can bypass them.
- Locking clears decrypted content from the interface, but Python cannot guarantee that sensitive key material is erased from memory. The app does not protect against malware or someone watching you type.

**Keep your master password and backups private.** A backup contains encrypted capsule data and a password-protected key envelope. Someone with a copy could attempt to guess the password offline. If you forget the password, the encrypted capsules cannot be recovered.

## Backups

Use **Settings > Backup and restore** to export or import a JSON backup. Imports are validated before they change the database. When duplicates are found, the app lets you choose whether to skip or overwrite them.

To restore a backup into a new, uninitialized vault, select **Restore from a backup** on the first-run screen and enter the password used to create that backup.

Backups may contain sensitive encrypted data. Store them securely, and do not upload them to a public repository.

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| Ctrl+1 through Ctrl+6 | Open Dashboard, New capsule, Library, Timeline, Reflection, or Settings |
| Ctrl+N | Create a capsule |
| Ctrl+F | Search the library |
| Ctrl+S | Save the capsule being written |
| Ctrl+L | Lock the vault |
| Ctrl+B | Collapse or expand the sidebar |

## Project structure

```text
main.py                 Application entry point
database.py             SQLite database access
models.py               Shared data models
services/               Capsule, security, backup, and settings logic
ui/                     CustomTkinter app, reusable components, and pages
utils/                  Date and input validation helpers
tests/                  unittest test suite
requirements.txt        Python dependencies
run_echo.bat            Windows setup and launch script
run_tests.bat           Windows test runner
```

## GitHub and contributions

Do not upload your `.venv`, local database or log files, exported backups, `.env` files, passwords, or other credentials. The repository's `.gitignore` excludes common local and sensitive files; review your changes before pushing.

There is currently no license file in this project. Add a license if you want to explicitly grant others permission to use, modify, or redistribute the code.
