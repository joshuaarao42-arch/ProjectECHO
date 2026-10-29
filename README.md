<div align="center">

# ✨ Project ECHO

### A private digital time capsule for the moments you want to revisit.

Write a letter to your future self, save a milestone, or capture a memory and choose when to open it.

![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Student project](https://img.shields.io/badge/made%20by-a%20CS%20student-7C3AED?style=for-the-badge)

**Created by Joshua C. Arao · First-year Computer Science student**

</div>

---

## 💭 What is Project ECHO?

Project ECHO is an offline-first Windows app for creating digital time capsules. Each capsule can hold a letter, journal entry, milestone, memory, or goal. Choose an unlock date, seal it away, and return when the time feels right.

Your vault is stored on your computer. Project ECHO does not use a cloud service or connect to a server.

## 🌟 Features

| | Feature | What you can do |
|---|---|---|
| ✍️ | **Create capsules** | Save letters, journal entries, milestones, memories, and goals with categories and tags. |
| 🔐 | **Protect your vault** | Encrypt capsule titles, tags, and text with AES-256-GCM; unlock the vault with a master password. |
| ⏳ | **Choose when to open** | Set an unlock date and view countdowns for locked capsules. |
| 🔎 | **Find and revisit** | Search and filter your library, browse a timeline, and compare unlocked entries. |
| 📊 | **Reflect** | See writing activity, category and tag counts, and time between entries. |
| 💾 | **Back up and restore** | Export encrypted backups and validate them before importing. |
| 🎨 | **Make it yours** | Choose light, dark, or system appearance. |

![image alt](https://github.com/joshuaarao42-arch/ProjectECHO/blob/main/ECHO/Screenshot%202026-10-30%20072953.png?raw=true)
![image alt](https://github.com/joshuaarao42-arch/ProjectECHO/blob/main/ECHO/Screenshot%202026-10-30%20073053.png?raw=true)
![image alt](https://github.com/joshuaarao42-arch/ProjectECHO/blob/main/ECHO/Screenshot%202026-10-30%20073105.png?raw=true)
![image alt](https://github.com/joshuaarao42-arch/ProjectECHO/blob/main/ECHO/Screenshot%202026-10-30%20073116.png?raw=true)
![image alt](https://github.com/joshuaarao42-arch/ProjectECHO/blob/main/ECHO/Screenshot%202026-10-30%20073129.png?raw=true)
![image alt](https://github.com/joshuaarao42-arch/ProjectECHO/blob/main/ECHO/Screenshot%202026-10-30%20073146.png?raw=true)
![image alt](https://github.com/joshuaarao42-arch/ProjectECHO/blob/main/ECHO/Screenshot%202026-10-30%20073203.png?raw=true)

## 🚀 Get started

### Requirements

- Windows
- Python 3.10 or newer with the Python `py` launcher

### Quick start

1. Install Python from [python.org](https://www.python.org/downloads/) and enable the Python launcher.
2. Download this repository and open its folder.
3. Double-click `run_echo.bat`. It creates a virtual environment and installs the required packages on first launch.

Or run these commands in Command Prompt from the project folder:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

On first launch, create a master password for your vault. **It cannot be recovered if you forget it.**

## 🧪 Run the tests

```bat
run_tests.bat
```

Or run the suite directly:

```bat
python -m unittest discover -s tests -t . -v
```

The tests use Python's built-in `unittest` framework and do not require a display.

## 🗂️ Project layout

```text
main.py                 App entry point
database.py            SQLite persistence
models.py               Shared data models
services/               Capsule, security, backup, and settings logic
ui/                     CustomTkinter app and screens
utils/                  Date and input validation helpers
tests/                  Automated tests
requirements.txt        Python dependencies
run_echo.bat            Windows setup and launch
run_tests.bat           Windows test runner
```

## 🛡️ Privacy and security

Capsule titles, tags, and text are encrypted at rest. A key derived from your master password with scrypt protects the encryption key. The database also stores some capsule metadata—such as categories, dates, and favorite or archived status—in the clear so the app can sort and filter your library.

Unlock dates are enforced by the app, not by cryptography. Someone who changes the system clock or modifies the software could bypass a date lock. Backups contain encrypted capsule data and should still be kept private; a copied backup could be used to attempt password guesses offline.

By default, app data is stored in `%LOCALAPPDATA%\ProjectECHO`. Set `ECHO_DATA_DIR` to choose another location. The app does not write capsule titles or text to its logs.

## ⌨️ Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+1` to `Ctrl+6` | Open Dashboard, New capsule, Library, Timeline, Reflection, or Settings |
| `Ctrl+N` | Create a capsule |
| `Ctrl+F` | Search the library |
| `Ctrl+S` | Save the capsule being written |
| `Ctrl+L` | Lock the vault |
| `Ctrl+B` | Collapse or expand the sidebar |

## 👋 About the author

Hi, I'm **Joshua C. Arao**, a first-year Computer Science student. I built Project ECHO as a way to explore Python desktop development, privacy-minded design, and the idea of writing to your future self.

Thanks for taking a look at my project! ⭐

---

<sub>Built with Python, CustomTkinter, and SQLite. Dependencies: [CustomTkinter](https://customtkinter.tomschimansky.com/) and [cryptography](https://cryptography.io/).</sub>
