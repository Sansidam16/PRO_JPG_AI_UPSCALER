"""Tema Tkinter sederhana agar tampilan GUI lebih rapi dan konsisten."""
from tkinter import ttk

BG = "#F4F5F7"
PANEL = "#FFFFFF"
ACCENT = "#0F6CBD"
TEXT = "#1F2328"
MUTED = "#57606A"


def apply_theme(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("TFrame", background=BG)
    style.configure("TLabelframe", background=BG, bordercolor="#D0D7DE")
    style.configure("TLabelframe.Label", background=BG, foreground=MUTED, font=("Segoe UI", 10, "bold"))
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("TButton", padding=(10, 5))
    style.configure("Accent.TButton", foreground="#FFFFFF", background=ACCENT)
    style.map("Accent.TButton", background=[("active", "#0B5AA0"), ("disabled", "#9DB8D6")])
    style.configure("TCheckbutton", background=BG)
    style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), background=BG)
    style.configure("Progressbar", background=ACCENT)
    return style
