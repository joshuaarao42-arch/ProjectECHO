"""Settings: appearance, security, backup and demonstration data."""
from __future__ import annotations

import logging
from tkinter import filedialog

import customtkinter as ctk

from services.backup_service import BackupError
from services.security_service import AuthenticationError
from services.settings_service import APPEARANCE_CHOICES, INACTIVITY_CHOICES
from ui import theme
from ui.components import (Card, ChoiceDialog, PageHeader, button, entry, label, muted, option_menu,
                           segmented, show_message)
from ui.pages.base import Page
from utils import dates
from utils.validation import ValidationError

log = logging.getLogger("echo.ui.settings")

PROTECTION_TEXT = (
    "Capsule titles, tags and text are encrypted on disk with AES-256-GCM. The key is protected by your master "
    "password (scrypt). If you lose the password, the capsules cannot be recovered.\n\n"
    "Unlock dates are enforced by this application, not by cryptography. Category, dates and favorite/archive "
    "flags are stored unencrypted so the library can sort them. Someone who can run modified software on this "
    "computer, or who changes the system clock, could bypass the date rule. Encryption protects the content "
    "from anyone who only has the database file."
)


def _section(parent, title: str, row: int, subtitle: str = "") -> Card:
    card = Card(parent)
    card.grid(row=row, column=0, sticky="ew", padx=theme.PAD, pady=6)
    label(card, title, style="heading").pack(anchor="w", padx=20, pady=(16, 0))
    if subtitle:
        muted(card, subtitle, style="body", wraplength=700).pack(anchor="w", padx=20, pady=(2, 0))
    return card


class SettingsPage(Page):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        PageHeader(body, "Settings", "Appearance, privacy and backups."
                   ).grid(row=0, column=0, sticky="ew", padx=theme.PAD, pady=(theme.PAD, 8))

        card = _section(body, "Appearance", 1)
        self.appearance = segmented(card, [m.title() for m in APPEARANCE_CHOICES], command=self._set_appearance)
        self.appearance.pack(anchor="w", padx=20, pady=(10, 18))

        card = _section(body, "Privacy and security", 2, "Lock automatically after a period without activity.")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(anchor="w", padx=20, pady=(10, 4))
        muted(row, "Inactivity timeout", style="body").pack(side="left", padx=(0, 10))
        self.timeout = option_menu(row, [f"{m} min" for m in INACTIVITY_CHOICES], command=self._set_timeout, width=110)
        self.timeout.pack(side="left")
        button(row, "Lock now", app.lock, kind="secondary", width=100).pack(side="left", padx=14)
        label(card, "Change master password", style="bold").pack(anchor="w", padx=20, pady=(14, 4))
        pw = ctk.CTkFrame(card, fg_color="transparent")
        pw.pack(anchor="w", padx=20)
        self.old_pw = entry(pw, "Current password", show="•", width=200)
        self.new_pw = entry(pw, "New password", show="•", width=200)
        self.new_pw2 = entry(pw, "Repeat new password", show="•", width=200)
        for widget in (self.old_pw, self.new_pw, self.new_pw2):
            widget.pack(side="left", padx=(0, 8))
        button(card, "Change password", self._change_password, width=160).pack(anchor="w", padx=20, pady=(10, 4))
        self.pw_status = label(card, "")
        self.pw_status.pack(anchor="w", padx=20, pady=(0, 14))

        card = _section(body, "How your data is protected", 3)
        muted(card, PROTECTION_TEXT, style="body", wraplength=720).pack(anchor="w", padx=20, pady=(8, 18))

        card = _section(body, "Backup and restore", 4,
                        "Backups are JSON files that keep capsules encrypted. They hold no plaintext content.")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(anchor="w", padx=20, pady=(10, 4))
        button(row, "Export backup", self._export, width=140).pack(side="left")
        button(row, "Import backup", self._import, kind="secondary", width=140).pack(side="left", padx=8)
        self.backup_status = label(card, "")
        self.backup_status.pack(anchor="w", padx=20, pady=(4, 16))

        card = _section(body, "Demonstration data", 5,
                        "Add a few clearly fictional capsules to explore the app. Nothing is added unless you ask.")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(anchor="w", padx=20, pady=(10, 18))
        self.demo_btn = button(row, "Load demo data", self._load_demo, kind="secondary", width=150)
        self.demo_btn.pack(side="left")
        self.demo_rm = button(row, "Remove demo data", self._remove_demo, kind="secondary", width=160)
        self.demo_rm.pack(side="left", padx=8)

    def on_show(self, **kwargs) -> None:
        s = self.app.settings.load()
        self.appearance.set(s.appearance.title())
        self.timeout.set(f"{s.inactivity_minutes} min")
        self._sync_demo()

    def clear_sensitive(self) -> None:
        for widget in (self.old_pw, self.new_pw, self.new_pw2):
            widget.delete(0, "end")
        self.pw_status.configure(text="")
        self.backup_status.configure(text="")

    def _sync_demo(self) -> None:
        loaded = self.app.capsules.demo_loaded
        self.demo_btn.configure(state="disabled" if loaded else "normal")
        self.demo_rm.configure(state="normal" if loaded else "disabled")

    def _set_appearance(self, value: str) -> None:
        self.app.settings.set_appearance(value.lower())
        ctk.set_appearance_mode(value.lower())

    def _set_timeout(self, value: str) -> None:
        self.app.settings.set_inactivity_minutes(int(value.split()[0]))
        self.app.notify("Inactivity timeout updated.", "success")

    def _change_password(self) -> None:
        if self.new_pw.get() != self.new_pw2.get():
            self.pw_status.configure(text="The new passwords do not match.", text_color=theme.DANGER)
            return
        self.pw_status.configure(text="Working…", text_color=theme.MUTED)
        self.update_idletasks()
        try:
            self.app.security.change_password(self.old_pw.get(), self.new_pw.get())
        except (AuthenticationError, ValidationError) as exc:
            self.pw_status.configure(text=str(exc), text_color=theme.DANGER)
            return
        self.clear_sensitive()
        self.pw_status.configure(text="Password changed.", text_color=theme.SUCCESS)

    def _export(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self, title="Export backup", defaultextension=".json",
            initialfile=f"echo-backup-{dates.now():%Y-%m-%d}.json", filetypes=[("ECHO backup", "*.json")])
        if not path:
            return
        self.backup_status.configure(text="Exporting…", text_color=theme.MUTED)
        self.update_idletasks()
        try:
            count = self.app.backup.export_backup(path)
        except OSError:
            log.exception("Export failed")
            self.backup_status.configure(text="The backup could not be written. Check the location and try again.",
                                         text_color=theme.DANGER)
            return
        self.backup_status.configure(text=f"Exported {count} capsule{'s' if count != 1 else ''}.", text_color=theme.SUCCESS)

    def _import(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Import backup", filetypes=[("ECHO backup", "*.json")])
        if not path:
            return
        self.backup_status.configure(text="Checking the file…", text_color=theme.MUTED)
        self.update_idletasks()
        report = self.app.backup.inspect_backup(path)
        if not report.valid:
            self.backup_status.configure(text="Import cancelled: the file did not pass validation.", text_color=theme.DANGER)
            show_message(self, "Backup not imported", "Nothing was changed.\n\n" + "\n".join(report.errors[:6]))
            return
        message = f"The file holds {report.total} capsule(s): {report.new} new, {report.duplicates} already here."
        if report.duplicates:
            choice = ChoiceDialog(self, "Duplicates found", message + "\n\nOverwriting replaces the stored copy, "
                                  "including favorite and archive flags.",
                                  [("Cancel", "cancel", "secondary"), ("Skip duplicates", "skip", "primary"),
                                   ("Overwrite", "overwrite", "danger")]).show()
        else:
            choice = ChoiceDialog(self, "Import backup", message,
                                  [("Cancel", "cancel", "secondary"), ("Import", "skip", "primary")]).show()
        if choice in (None, "cancel"):
            self.backup_status.configure(text="Import cancelled.", text_color=theme.MUTED)
            return
        try:
            result = self.app.backup.import_backup(path, overwrite=choice == "overwrite")
        except BackupError as exc:
            self.backup_status.configure(text=str(exc), text_color=theme.DANGER)
            return
        self.backup_status.configure(
            text=f"Imported: {result.added} added, {result.skipped} skipped, {result.overwritten} overwritten.",
            text_color=theme.SUCCESS)

    def _load_demo(self) -> None:
        self.app.capsules.load_demo_data()
        self._sync_demo()
        self.app.notify("Demonstration data added.", "success")

    def _remove_demo(self) -> None:
        self.app.capsules.remove_demo_data()
        self._sync_demo()
        self.app.notify("Demonstration data removed.")
