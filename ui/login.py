from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from services.backup_service import BackupError
from services.security_service import AuthenticationError
from ui import theme
from ui.components import Card, button, entry, label, muted
from utils.validation import ValidationError


class LoginView(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self.grid_rowconfigure((0, 2), weight=1)
        self.grid_columnconfigure((0, 2), weight=1)
        card = Card(self)
        card.grid(row=1, column=1, padx=24, pady=24)

        label(card, "E C H O", style="logo_big", color=theme.CYAN, anchor="center", justify="center").pack(padx=60, pady=(34, 0))
        muted(card, "A private time capsule for the person you are becoming.", style="body",
              anchor="center", justify="center", wraplength=330).pack(padx=30, pady=(4, 18))
        self.heading = label(card, "", style="heading")
        self.heading.pack(anchor="w", padx=40)
        self.hint = muted(card, "", wraplength=330)
        self.hint.pack(anchor="w", padx=40, pady=(0, 8))
        self.password = entry(card, "Master password", show="•", width=330)
        self.password.pack(padx=40, pady=4)
        self.confirm = entry(card, "Repeat master password", show="•", width=330)
        self.confirm.pack(padx=40, pady=4)
        self.status = label(card, "", wraplength=330, color=theme.DANGER)
        self.status.pack(anchor="w", padx=40, pady=(6, 0))
        self.submit_btn = button(card, "", self.submit, width=330, height=40)
        self.submit_btn.pack(padx=40, pady=(10, 4))
        self.restore_btn = button(card, "Restore from a backup", self._restore, kind="ghost", width=330)
        self.restore_btn.pack(padx=40, pady=(0, 28))
        for widget in (self.password, self.confirm):
            widget.bind("<Return>", lambda _e: self.submit())
        self.refresh_mode()

    @property
    def _setup_mode(self) -> bool:
        return not self.app.security.is_initialized

    def refresh_mode(self, message: str = "") -> None:
        self.password.delete(0, "end")
        self.confirm.delete(0, "end")
        self.status.configure(text=message, text_color=theme.MUTED if message else theme.DANGER)
        if self._setup_mode:
            self.heading.configure(text="Create your vault")
            self.hint.configure(text="Choose a master password (10+ characters). It cannot be recovered if you forget it.")
            self.confirm.pack(padx=40, pady=4, after=self.password)
            self.submit_btn.configure(text="Create vault")
            self.restore_btn.pack(padx=40, pady=(0, 28))
        else:
            self.heading.configure(text="Welcome back")
            self.hint.configure(text="Enter your master password to unlock your capsules.")
            self.confirm.pack_forget()
            self.submit_btn.configure(text="Unlock")
            self.restore_btn.pack_forget()
        self.password.focus_set()

    def submit(self) -> None:
        password = self.password.get()
        self.status.configure(text="")
        if self._setup_mode and password != self.confirm.get():
            self.status.configure(text="The passwords do not match.", text_color=theme.DANGER)
            return
        self.submit_btn.configure(state="disabled", text="Working…")
        self.update_idletasks()
        try:
            if self._setup_mode:
                self.app.security.setup(password)
            else:
                self.app.security.unlock(password)
        except (ValidationError, AuthenticationError) as exc:
            self.status.configure(text=str(exc), text_color=theme.DANGER)
            self.submit_btn.configure(state="normal", text="Create vault" if self._setup_mode else "Unlock")
            self.password.delete(0, "end")
            return
        self.submit_btn.configure(state="normal")
        self.password.delete(0, "end")
        self.confirm.delete(0, "end")
        self.app.on_unlocked()

    def _restore(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Choose an ECHO backup", filetypes=[("ECHO backup", "*.json")])
        if not path:
            return
        try:
            self.app.backup.restore_key_envelope(path)
        except BackupError as exc:
            self.status.configure(text=str(exc), text_color=theme.DANGER)
            return
        self.app.pending_restore = path
        self.refresh_mode("Backup found. Enter the master password you used when you made it; "
                          "your capsules will be imported after unlocking.")
