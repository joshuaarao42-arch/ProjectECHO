# Contributing to Project ECHO

Thank you for contributing to Project ECHO, an offline-first Windows time-capsule application for saving entries and revisiting them on a chosen date.

## Set up the project
```bash
git clone https://github.com/joshuaarao42-arch/ProjectECHO.git
cd ProjectECHO
```
Use Python 3.10 or newer and follow the dependency and launch instructions in the README.

## Contribution areas
- Capsule creation, categories, tags, search, and timeline browsing.
- Unlock-date handling and countdown presentation.
- Vault usability, backup, restore, and validation.
- Writing activity summaries and appearance settings.
- Reliability and clarity of encryption-related workflows.

## Security and privacy are essential
- Never weaken encryption, password handling, or key derivation to simplify a feature.
- Do not log capsule contents, passwords, keys, or other private material.
- Never commit real vault files, backups, or personal letters.
- Treat backup import as untrusted input and validate it before modifying local data.
- Security-sensitive changes should explain the threat addressed and how they were tested.

## Testing and pull requests
Test locked and unlocked capsules, date boundaries, search and filters, backup export/import, and malformed backup files where relevant. Use fictional capsule content in demonstrations.

Use branches such as `feature/capsule-search` or `fix/backup-validation`. Include clear test notes, especially for privacy or encryption changes.
