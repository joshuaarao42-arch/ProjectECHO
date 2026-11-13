# Contributing to Project ECHO contribution guide

Thank you for your interest in improving this project.

## Project overview

Project ECHO contribution guide is maintained through community contributions, bug fixes, testing, and documentation improvements.

## Getting started

```bash
git clone https://github.com/joshuaarao42-arch/ProjectECHO.git
cd ProjectECHO
```

Follow the README for any additional dependencies or platform-specific setup. Review the existing code before changing project structure.

## Contribution areas

Improve capsule creation, search, tags, unlock dates, vault usability, and backup and restore.

Documentation, accessibility, and reproducible bug fixes are welcome too.

## Project-specific checks

Protect private entries and encryption. Never commit vault files, passwords, or keys. Validate imported backups and test that failed imports do not damage existing data.

## Coding guidelines

- Follow existing language, naming, formatting, and folder conventions.
- Keep changes focused and explain non-obvious logic.
- Validate inputs and handle errors clearly.
- Avoid unrelated refactoring or unnecessary dependencies.
- Never commit secrets, credentials, private records, or generated local data.

## Testing

Run the application and test all workflows affected by your change, including relevant edge cases. State the environment and tests performed. Include screenshots for interface changes and sample inputs with expected results for logic changes.

## Branches and commits

Create a branch from the default branch using a descriptive name, such as `feature/short-description`, `fix/short-description`, or `docs/short-description`.

Use commit prefixes consistently: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, and `test:`.

## Pull requests

Explain the problem, summarize the solution, link a related issue when available, and list the tests and results. Add screenshots or sample output when useful. Mention new dependencies, compatibility changes, and known limitations.

## Issues and feature requests

Search existing issues first. Include reproduction steps, expected and actual behavior, environment details, and sanitized logs or screenshots. Feature requests should explain the use case and expected benefit.

## Code of conduct

Be respectful, patient, and constructive. Critique code and ideas rather than people. Harassment, discrimination, and abusive behavior are not acceptable.


## Running the automated test suite

From the repository root, run `python -m unittest discover -s tests -t . -v`. On Windows, you can also use `run_tests.bat`. Include the command and its result in your pull request description when relevant.
