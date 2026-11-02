# Contributing to Project ECHO

Project ECHO is an offline-first Windows time capsule app for writing entries, setting unlock dates, and revisiting memories later.

## Clone
```bash
git clone https://github.com/joshuaarao42-arch/ProjectECHO.git
cd ProjectECHO
```
Use Python 3.10 or newer and follow the README's dependency and launch instructions.

## Project-specific contributions
- Capsule creation, categories, tags, search, and timeline browsing.
- Unlock-date logic and countdowns.
- Vault usability, backup, restore, and validation.
- Writing summaries and appearance settings.

## Privacy and security
Never weaken encryption, password handling, or key derivation to simplify a feature. Do not log capsule contents, passwords, or keys. Never commit real vault files, backups, or personal letters. Treat imported backups as untrusted input and validate them before changing local data.

Test locked/unlocked entries, date boundaries, search, backup export/import, and malformed backup files where relevant. Use fictional content in demonstrations. Security-related pull requests must explain the risk addressed and tests performed.
