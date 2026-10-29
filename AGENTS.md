# Repository Guidelines

## Project Structure & Module Organization

`main.py` starts the Windows desktop app. Core persistence and data types live in `database.py` and `models.py`. Keep application logic in `services/` (capsules, security, backups, and settings), shared date and input helpers in `utils/`, and CustomTkinter screens and widgets in `ui/`. Add automated checks under `tests/`, matching the module or service they cover. User data belongs in `%LOCALAPPDATA%\ProjectECHO`; do not commit databases, logs, virtual environments, or secrets.

## Build, Test, and Development Commands

Use Python 3.10 or later on Windows. Set up and launch locally with:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

`run_echo.bat` automates first-run setup and app launch. Run the full unittest suite with `run_tests.bat`, or use `python -m unittest discover -s tests -t . -v` from the repository root. Tests need the declared dependencies but do not require a display.

## Coding Style & Naming Conventions

Follow the existing Python style: four spaces per indent, descriptive `snake_case` functions and variables, `PascalCase` classes, and uppercase constants. Keep UI code in `ui/`, business rules in services, and reusable validation/date logic in `utils/`. Use parameterized SQL through the database layer. Do not add plaintext capsule content to logs, notifications, or activity records. No formatter or linter is configured; keep changes consistent with adjacent files.

## Testing Guidelines

Tests use Python's built-in `unittest`. Name files `test_<area>.py` and test methods `test_<behavior>`. Add or update coverage for changed validation, access control, encryption, database, and backup behavior. Run the full suite with the command above before submitting.

## Commit & Pull Request Guidelines

This checkout has no Git history to establish commit conventions. Use a short imperative commit subject, such as `Validate backup records before import`. PRs should describe the user-visible change, note security or data-format impact, link related issues, and include screenshots for UI changes. State the test command and its result.

## Security & Configuration Tips

Keep credentials, `.env` files, exported backups, and local data out of version control. Treat backup files as sensitive: they contain encrypted capsule data that may be targeted for offline password guessing. Preserve all-or-nothing import validation and never claim unlock dates are cryptographic enforcement.
