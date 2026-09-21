import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import hashlib
import csv
import json
import logging
import os
import re
from datetime import datetime, date

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

if not os.path.exists('app_logging'):
    os.makedirs('app_logging')
logging.basicConfig(filename='app_logging/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

failed_attempts = {}
CHECK_EMPTY, CHECK_FILLED = "☐", "☑"

FONT_MAIN = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_DIGITAL = ("Consolas", 12, "bold")

# ============================================================
# THEME SYSTEM (Light / Dim / Dark) - shared by every window
# ============================================================
THEME_SETTINGS_FILE = "theme_settings.json"

THEMES = {
    "Light": {
        "bg_main": "#F5F6FA", "bg_card": "#FFFFFF", "bg_header": "#FFFFFF",
        "bg_panel": "#F0F1F6", "bg_tree_head": "#EDEFF5", "bg_log": "#FAFBFC",
        "text_main": "#2E3348", "text_muted": "#6B7280", "border": "#E1E4EB",
        "accent": "#5C7CFA", "accent_hover": "#4C6FE0", "amber": "#D9822B",
        "success": "#2F9E63", "danger": "#E5534B", "danger_strong": "#B42318",
        "purple": "#8B7CF6", "tint_danger": "#FDECEA", "tint_warn": "#FDF3E3",
        "tint_success": "#E8F7EE", "select_bg": "#D7DBEA", "select_fg": "#20243A",
        "btn_fg": "#FFFFFF",
    },
    "Dim": {
        "bg_main": "#1E2230", "bg_card": "#262B3D", "bg_header": "#262B3D",
        "bg_panel": "#2B3145", "bg_tree_head": "#323950", "bg_log": "#20242F",
        "text_main": "#E4E6EF", "text_muted": "#9CA3B5", "border": "#3B4258",
        "accent": "#7C9BFF", "accent_hover": "#6B87E0", "amber": "#E5A44E",
        "success": "#4CBE84", "danger": "#F17872", "danger_strong": "#FF8A80",
        "purple": "#A796F8", "tint_danger": "#3A2830", "tint_warn": "#3A3325",
        "tint_success": "#243A31", "select_bg": "#3B4258", "select_fg": "#FFFFFF",
        "btn_fg": "#FFFFFF",
    },
    "Dark": {
        "bg_main": "#121317", "bg_card": "#191B21", "bg_header": "#191B21",
        "bg_panel": "#1D2027", "bg_tree_head": "#22252E", "bg_log": "#0F1115",
        "text_main": "#EDEEF3", "text_muted": "#8A8F9E", "border": "#2A2E38",
        "accent": "#7C9BFF", "accent_hover": "#6B87E0", "amber": "#E5A44E",
        "success": "#4CBE84", "danger": "#F17872", "danger_strong": "#FF8A80",
        "purple": "#A796F8", "tint_danger": "#2B1B1E", "tint_warn": "#2B2519",
        "tint_success": "#182821", "select_bg": "#2A2E38", "select_fg": "#FFFFFF",
        "btn_fg": "#FFFFFF",
    },
}
THEME_NAMES = ["Light", "Dim", "Dark"]

def load_theme_setting():
    try:
        with open(THEME_SETTINGS_FILE, "r") as f:
            return json.load(f).get("theme", "Light")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return "Light"

def save_theme_setting(name):
    try:
        with open(THEME_SETTINGS_FILE, "w") as f:
            json.dump({"theme": name}, f)
    except OSError:
        pass

def apply_theme(name):
    """Applies a theme mode app-wide (all users, all screens) and persists it."""
    global CURRENT_THEME, BG_MAIN, BG_CARD, BG_HEADER, BG_PANEL, BG_TREE_HEAD, BG_LOG
    global TEXT_MAIN, TEXT_MUTED, BORDER, ACCENT_CYAN, ACCENT_HOVER, ACCENT_AMBER
    global SUCCESS_GREEN, DANGER_RED, DANGER_STRONG, BTN_PURPLE
    global TINT_DANGER, TINT_WARN, TINT_SUCCESS, SELECT_BG, SELECT_FG, BTN_FG

    if name not in THEMES:
        name = "Light"
    t = THEMES[name]
    CURRENT_THEME = name

    BG_MAIN, BG_CARD, BG_HEADER = t["bg_main"], t["bg_card"], t["bg_header"]
    BG_PANEL, BG_TREE_HEAD, BG_LOG = t["bg_panel"], t["bg_tree_head"], t["bg_log"]
    TEXT_MAIN, TEXT_MUTED, BORDER = t["text_main"], t["text_muted"], t["border"]
    ACCENT_CYAN, ACCENT_HOVER, ACCENT_AMBER = t["accent"], t["accent_hover"], t["amber"]
    SUCCESS_GREEN, DANGER_RED, DANGER_STRONG = t["success"], t["danger"], t["danger_strong"]
    BTN_PURPLE = t["purple"]
    TINT_DANGER, TINT_WARN, TINT_SUCCESS = t["tint_danger"], t["tint_warn"], t["tint_success"]
    SELECT_BG, SELECT_FG, BTN_FG = t["select_bg"], t["select_fg"], t["btn_fg"]

    save_theme_setting(name)

def configure_ttk_style(style):
    """Applies the current theme to every shared ttk widget style (Notebook,
    LabelFrame, Treeview, Combobox, Scrollbar) so ttk widgets match tk widgets."""
    style.theme_use("clam")

    style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
    style.configure("TNotebook.Tab", background=BG_CARD, foreground=TEXT_MUTED, font=FONT_BOLD, padding=[15, 5], borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", BG_MAIN)], foreground=[("selected", ACCENT_CYAN)])

    style.configure("TLabelframe", background=BG_MAIN, bordercolor=BORDER)
    style.configure("TLabelframe.Label", background=BG_MAIN, foreground=ACCENT_CYAN, font=FONT_BOLD)

    style.configure("Treeview", background=BG_CARD, fieldbackground=BG_CARD, foreground=TEXT_MAIN, rowheight=30, borderwidth=0, font=FONT_MAIN)
    style.configure("Treeview.Heading", background=BG_TREE_HEAD, foreground=TEXT_MAIN, font=FONT_BOLD, borderwidth=1, bordercolor=BORDER, padding=[0, 5])
    style.map("Treeview", background=[("selected", SELECT_BG)], foreground=[("selected", SELECT_FG)])

    style.configure("TCombobox", fieldbackground=BG_CARD, background=BG_CARD, foreground=TEXT_MAIN, arrowcolor=TEXT_MAIN, bordercolor=BORDER)
    style.map("TCombobox",
              fieldbackground=[("readonly", BG_CARD)],
              foreground=[("readonly", TEXT_MAIN)],
              selectbackground=[("readonly", BG_CARD)],
              selectforeground=[("readonly", TEXT_MAIN)])

    style.configure("Vertical.TScrollbar", background=BG_PANEL, troughcolor=BG_MAIN, bordercolor=BORDER, arrowcolor=TEXT_MAIN)


def create_theme_selector(parent, on_change, bg):
    """A small 'Light / Dim / Dark' dropdown used on every screen (auth + app)."""
    wrap = tk.Frame(parent, bg=bg)
    tk.Label(wrap, text="Theme:", font=FONT_MAIN, bg=bg, fg=TEXT_MUTED).pack(side="left", padx=(0, 5))
    var = tk.StringVar(value=CURRENT_THEME)
    combo = ttk.Combobox(wrap, textvariable=var, values=THEME_NAMES, state="readonly", font=FONT_MAIN, width=7)
    combo.pack(side="left")
    combo.bind("<<ComboboxSelected>>", lambda e: on_change(var.get()))
    return wrap

def add_password_toggle(parent, entry):
    """Packs a 'show/hide' eye button next to a password Entry, side-by-side.
    Returns the toggle button in case the caller wants to place/theme it further."""
    def toggle():
        if entry.cget("show") == "":
            entry.config(show="•")
            toggle_btn.config(text="👁")
        else:
            entry.config(show="")
            toggle_btn.config(text="🙈")

    toggle_btn = tk.Button(parent, text="👁", width=3, command=toggle, bg=BG_CARD, fg=TEXT_MUTED,
                            relief="flat", cursor="hand2", highlightthickness=1, highlightbackground=BORDER)
    return toggle_btn


def ask_password_with_toggle(parent, title, prompt):
    """A themed modal password prompt with a show/hide toggle (replacement for
    simpledialog.askstring(show='*'), which cannot show the typed value)."""
    result = {"value": None}
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.configure(bg=BG_MAIN)
    dialog.geometry("360x180")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    tk.Label(dialog, text=prompt, font=FONT_MAIN, bg=BG_MAIN, fg=TEXT_MAIN, wraplength=320, justify="left").pack(padx=20, pady=(20, 10), anchor="w")

    entry_frame = tk.Frame(dialog, bg=BG_MAIN)
    entry_frame.pack(fill="x", padx=20)
    entry = tk.Entry(entry_frame, show="•", font=FONT_MAIN, bg=BG_CARD, fg=ACCENT_CYAN, insertbackground=ACCENT_CYAN,
                      relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT_CYAN)
    entry.pack(side="left", fill="x", expand=True, ipady=5)
    entry.focus_set()

    toggle_btn = add_password_toggle(entry_frame, entry)
    toggle_btn.pack(side="left", padx=(6, 0))

    def submit(event=None):
        result["value"] = entry.get()
        dialog.destroy()

    def cancel():
        dialog.destroy()

    entry.bind("<Return>", submit)

    btn_frame = tk.Frame(dialog, bg=BG_MAIN)
    btn_frame.pack(fill="x", padx=20, pady=20)
    tk.Button(btn_frame, text="Cancel", command=cancel, bg=BG_MAIN, fg=TEXT_MUTED, font=FONT_MAIN, relief="flat", cursor="hand2").pack(side="right", padx=(10, 0))
    tk.Button(btn_frame, text="Save", command=submit, bg=ACCENT_CYAN, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", padx=15).pack(side="right")

    dialog.wait_window()
    return result["value"]


# ============================================================
# MISSING / NOT-RETURNED-IN-24HRS AUTO-FLAGGING
# ============================================================
def check_missing_borrows(conn):
    """Any APPROVED borrow that is 24+ hours past its due date gets flagged
    MISSING (not returned). Runs against the given open connection; caller
    is responsible for closing it."""
    today = date.today()
    rows = conn.execute("SELECT request_id, due_date FROM borrow_requests WHERE status='APPROVED'").fetchall()
    changed = False
    for req_id, due in rows:
        try:
            due_date_obj = datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            continue
        if (today - due_date_obj).days >= 2:
            conn.execute("UPDATE borrow_requests SET status='MISSING' WHERE request_id=?", (req_id,))
            logging.warning(f"Borrow request #{req_id} auto-flagged as MISSING (not returned within 24hrs of due date).")
            changed = True
    if changed:
        conn.commit()


apply_theme(load_theme_setting())

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def calculate_status(quantity):
    return "In Stock" if quantity >= 10 else "Low Stock" if quantity >= 1 else "Out of Stock"

def today_str():
    return date.today().isoformat()

def sync_hardware_status(conn, item_id):
    qty = conn.execute("SELECT quantity FROM hardware WHERE item_id=?", (item_id,)).fetchone()[0]
    conn.execute("UPDATE hardware SET status=? WHERE item_id=?", (calculate_status(qty), item_id))

def init_db():
    conn = sqlite3.connect("hardware_inventory.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hardware (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL, category TEXT NOT NULL,
        quantity INTEGER NOT NULL, unit_price REAL NOT NULL, status TEXT NOT NULL
    )""")
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, role TEXT NOT NULL, status TEXT DEFAULT 'ACTIVE'
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reset_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL, email TEXT NOT NULL, status TEXT DEFAULT 'PENDING'
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS borrow_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        request_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING',
        return_date TEXT
    )""")
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                       ('admin', 'admin@nu.edu.ph', hash_password('Admin@123'), 'ADMIN'))
    conn.commit()
    conn.close()

class AuthWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("System Authentication")
        self.master.geometry("400x560")
        self.master.configure(bg=BG_MAIN)
        self.is_login_mode = True
        self.style = ttk.Style()
        configure_ttk_style(self.style)
        self.build_ui()

    def change_theme(self, name):
        apply_theme(name)
        configure_ttk_style(self.style)
        self.master.configure(bg=BG_MAIN)
        self.build_ui()

    def build_ui(self):
        for widget in self.master.winfo_children(): widget.destroy()

        tk.Frame(self.master, bg=ACCENT_CYAN, height=4).pack(fill="x")

        top_bar = tk.Frame(self.master, bg=BG_MAIN)
        top_bar.pack(fill="x", padx=15, pady=(10, 0))
        create_theme_selector(top_bar, self.change_theme, BG_MAIN).pack(side="right")

        title = "Midterm Laboratory Exam" if self.is_login_mode else "Register New Account"
        tk.Label(self.master, text=title, font=("Segoe UI", 14, "bold"), bg=BG_MAIN, fg=ACCENT_CYAN).pack(pady=(20, 25))

        entry_config = {"font": FONT_MAIN, "bg": BG_CARD, "fg": ACCENT_CYAN, "insertbackground": ACCENT_CYAN, "relief": "flat", "highlightthickness": 1, "highlightbackground": BORDER, "highlightcolor": ACCENT_CYAN}

        if not self.is_login_mode:
            tk.Label(self.master, text="Email Address", font=FONT_BOLD, bg=BG_MAIN, fg=TEXT_MUTED).pack(anchor="w", padx=60)
            self.email_entry = tk.Entry(self.master, width=35, **entry_config)
            self.email_entry.pack(pady=(0, 15), ipady=5)

            tk.Label(self.master, text="Clearance Level", font=FONT_BOLD, bg=BG_MAIN, fg=TEXT_MUTED).pack(anchor="w", padx=60)
            self.role_entry = ttk.Combobox(self.master, values=["USER", "ADMIN"], state="readonly", font=FONT_MAIN)
            self.role_entry.current(0)
            self.role_entry.pack(pady=(0, 15), ipady=5)

        tk.Label(self.master, text="Username", font=FONT_BOLD, bg=BG_MAIN, fg=TEXT_MUTED).pack(anchor="w", padx=60)
        self.user_entry = tk.Entry(self.master, width=35, **entry_config)
        self.user_entry.pack(pady=(0, 15), ipady=5, fill="x", padx=60)

        tk.Label(self.master, text="Password", font=FONT_BOLD, bg=BG_MAIN, fg=TEXT_MUTED).pack(anchor="w", padx=60)
        pw_frame = tk.Frame(self.master, bg=BG_MAIN)
        pw_frame.pack(pady=(0, 20), fill="x", padx=60)
        self.pw_entry = tk.Entry(pw_frame, show="•", **entry_config)
        self.pw_entry.pack(side="left", fill="x", expand=True, ipady=5)
        add_password_toggle(pw_frame, self.pw_entry).pack(side="left", padx=(6, 0))

        btn_text = "Enter" if self.is_login_mode else "Register"
        tk.Button(self.master, text=btn_text, command=self.process, bg=ACCENT_CYAN, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", activebackground=ACCENT_HOVER, activeforeground=BTN_FG).pack(fill="x", padx=60, pady=5, ipady=8)

        if self.is_login_mode:
            tk.Button(self.master, text="Reset Account", command=self.request_reset, bg=BG_MAIN, fg=ACCENT_AMBER, font=FONT_MAIN, relief="flat", cursor="hand2", activebackground=BG_MAIN, activeforeground=ACCENT_AMBER).pack(pady=(15, 5))

        switch_text = "Create New Account" if self.is_login_mode else "Back to Login"
        tk.Button(self.master, text=switch_text, command=self.switch_mode, bg=BG_MAIN, fg=TEXT_MUTED, font=FONT_MAIN, relief="flat", cursor="hand2", activebackground=BG_MAIN, activeforeground=TEXT_MUTED).pack(pady=5)

    def switch_mode(self):
        self.is_login_mode = not self.is_login_mode
        self.build_ui()

    def request_reset(self):
        username = simpledialog.askstring("Reset Request", "Enter Username:")
        email = simpledialog.askstring("Reset Request", "Enter Registered Email:")
        if username and email:
            conn = sqlite3.connect("hardware_inventory.db")
            conn.execute("INSERT INTO reset_requests (username, email) VALUES (?, ?)", (username, email))
            conn.commit()
            conn.close()
            logging.info(f"Password reset requested for {username}")
            messagebox.showinfo("Sent", "Reset request sent to Admin.")

    def process(self):
        username = self.user_entry.get().strip()
        password = self.pw_entry.get().strip()
        conn = sqlite3.connect("hardware_inventory.db")
        cursor = conn.cursor()

        if self.is_login_mode:

            cursor.execute("SELECT status, role, password FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user:
                if user[0] == 'LOCKED':
                    messagebox.showerror("Locked", "Account locked. Request a password reset.")
                    return
                if user[2] == hash_password(password):
                    failed_attempts[username] = 0
                    logging.info(f"User {username} logged in successfully.")
                    self.master.destroy()
                    launch_main(username, user[1])
                else:

                    failed_attempts[username] = failed_attempts.get(username, 0) + 1
                    if failed_attempts[username] >= 3:
                        cursor.execute("UPDATE users SET status = 'LOCKED' WHERE username = ?", (username,))
                        conn.commit()
                        logging.warning(f"Account permanently locked for {username} after 3 attempts.")
                        messagebox.showerror("Locked", "3 failed attempts. Account permanently locked.")
                    else:
                        messagebox.showerror("Error", f"Invalid credentials. Attempts: {failed_attempts[username]}/3")
            else:
                messagebox.showerror("Error", "User not found.")
        else:

            email, role = self.email_entry.get().strip(), self.role_entry.get()
            if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password):
                messagebox.showerror("Validation", "Password needs 8 chars, 1 uppercase, 1 number.")
                return
            try:
                cursor.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                               (username, email, hash_password(password), role))
                conn.commit()
                logging.info(f"New user registered: {username} ({role})")
                messagebox.showinfo("Success", "Registered successfully!")
                self.switch_mode()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Username or Email exists.")
        conn.close()

class InventoryApp:
    def __init__(self, master, username, role):
        self.master = master
        self.username = username
        self.role = role
        title_suffix = "(ADMIN PANEL)" if role == "ADMIN" else "(USER PANEL)"
        self.master.title(f"Campus Hardware Inventory System {title_suffix}")
        self.master.geometry("1200x840")
        self.master.configure(bg=BG_MAIN)

        self.categories = ["Microcontroller", "Sensors", "IC", "Measurement", "Supply", "LED", "Components", "Tools"]

        self.style = ttk.Style()
        self.setup_styles()
        self.build_ui()
        self.load_data()
        self.load_borrow_data()
        self.refresh_dashboard()
        if self.role == "ADMIN":
            self.load_approvals()
            self.refresh_logs()
        self.schedule_missing_check()

    def schedule_missing_check(self):
        """Periodically re-checks for borrows that just crossed the 24hr-overdue
        mark so the UI updates even if nobody manually refreshes."""
        self.master.after(120000, self.periodic_missing_check)

    def periodic_missing_check(self):
        conn = sqlite3.connect("hardware_inventory.db")
        check_missing_borrows(conn)
        conn.close()
        self.load_borrow_data()
        self.refresh_dashboard()
        self.schedule_missing_check()

    def setup_styles(self):
        configure_ttk_style(self.style)

    def change_theme(self, name):
        apply_theme(name)
        self.rebuild_ui()

    def rebuild_ui(self):
        """Re-applies the current theme across the whole app window (all tabs)."""
        for widget in self.master.winfo_children():
            widget.destroy()
        self.master.configure(bg=BG_MAIN)
        self.setup_styles()
        self.build_ui()
        self.load_data()
        self.load_borrow_data()
        self.refresh_dashboard()
        if self.role == "ADMIN":
            self.load_approvals()
            self.refresh_logs()

    def build_ui(self):
        header = tk.Frame(self.master, bg=BG_HEADER, height=45, highlightthickness=1, highlightbackground=BORDER)
        header.pack(fill="x")
        header.pack_propagate(False)

        role_color = ACCENT_AMBER if self.role == "ADMIN" else ACCENT_CYAN
        tk.Label(header, text=f"Logged in as: {self.username} ", font=FONT_BOLD, bg=BG_HEADER, fg=TEXT_MAIN).pack(side="left", padx=(20, 0), pady=10)
        tk.Label(header, text=f"[{self.role}]", font=FONT_BOLD, bg=BG_HEADER, fg=role_color).pack(side="left", pady=10)

        tk.Button(header, text="Logout", command=self.logout, bg=DANGER_RED, fg=BTN_FG, font=FONT_BOLD, relief="flat", padx=10, cursor="hand2").pack(side="right", padx=20, pady=5)
        create_theme_selector(header, self.change_theme, BG_HEADER).pack(side="right", padx=(0, 20), pady=5)

        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(5, 10))

        self.tab_dashboard = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_dashboard, text="Dashboard")
        self.build_dashboard_tab()

        self.tab_catalog = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_catalog, text="Hardware Catalog")
        self.build_catalog_tab()

        self.tab_borrow = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_borrow, text="Borrow / Return")
        self.build_borrow_tab()

        if self.role == "ADMIN":
            self.tab_approvals = tk.Frame(self.notebook, bg=BG_MAIN)
            self.notebook.add(self.tab_approvals, text="Admin Approvals")
            self.build_approvals_tab()

            self.tab_logs = tk.Frame(self.notebook, bg=BG_MAIN)
            self.notebook.add(self.tab_logs, text="System Logs")
            self.build_logs_tab()

    def build_catalog_tab(self):
        entry_cfg = {"font": FONT_MAIN, "bg": BG_CARD, "fg": ACCENT_CYAN, "insertbackground": ACCENT_CYAN, "relief": "flat", "highlightthickness": 1, "highlightbackground": BORDER, "highlightcolor": ACCENT_CYAN}

        filter_frame = ttk.LabelFrame(self.tab_catalog, text=" 🔍 Search & Filter Components ")
        filter_frame.pack(fill="x", pady=(0, 5))

        tk.Label(filter_frame, text="Search Name:", bg=BG_MAIN, fg=TEXT_MAIN).pack(side="left", padx=10, pady=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.load_data())
        tk.Entry(filter_frame, textvariable=self.search_var, width=25, **entry_cfg).pack(side="left", ipady=3)

        tk.Label(filter_frame, text="Category:", bg=BG_MAIN, fg=TEXT_MAIN).pack(side="left", padx=10, pady=5)
        self.cat_filter_var = tk.StringVar()
        cat_filter = ttk.Combobox(filter_frame, textvariable=self.cat_filter_var, values=["ALL"] + self.categories, state="readonly", font=FONT_MAIN)
        cat_filter.current(0)
        cat_filter.bind("<<ComboboxSelected>>", lambda e: self.load_data())
        cat_filter.pack(side="left", ipady=3)

        val_frame = tk.Frame(self.tab_catalog, bg=BG_PANEL)
        val_frame.pack(fill="x", pady=5)
        self.lbl_valuation = tk.Label(val_frame, text="Total Asset Valuation: ₱0.00", font=FONT_DIGITAL, bg=BG_PANEL, fg=SUCCESS_GREEN)
        self.lbl_valuation.pack(pady=5)

        if self.role == "ADMIN":

            add_frame = ttk.LabelFrame(self.tab_catalog, text=" Admin Controls - Add Component ")
            add_frame.pack(fill="x", pady=5)

            tk.Label(add_frame, text="Item Name:", bg=BG_MAIN, fg=TEXT_MAIN).grid(row=0, column=0, padx=10, pady=5, sticky="e")
            self.entry_name = tk.Entry(add_frame, width=20, **entry_cfg)
            self.entry_name.grid(row=0, column=1, pady=5, ipady=3)
            self.entry_name.bind("<KeyRelease>", self.check_duplicate_name)

            tk.Label(add_frame, text="Category:", bg=BG_MAIN, fg=TEXT_MAIN).grid(row=0, column=2, padx=10, pady=5, sticky="e")
            self.combo_add_cat = ttk.Combobox(add_frame, values=self.categories, state="readonly", font=FONT_MAIN, width=18)
            self.combo_add_cat.current(0)
            self.combo_add_cat.grid(row=0, column=3, pady=5, ipady=3)

            tk.Label(add_frame, text="Quantity:", bg=BG_MAIN, fg=TEXT_MAIN).grid(row=1, column=0, padx=10, pady=5, sticky="e")
            self.entry_qty = tk.Entry(add_frame, width=20, **entry_cfg)
            self.entry_qty.grid(row=1, column=1, pady=5, ipady=3)

            tk.Label(add_frame, text="Unit Price (₱):", bg=BG_MAIN, fg=TEXT_MAIN).grid(row=1, column=2, padx=10, pady=5, sticky="e")
            self.entry_price = tk.Entry(add_frame, width=20, **entry_cfg)
            self.entry_price.grid(row=1, column=3, pady=5, ipady=3)

            tk.Button(add_frame, text="Save Hardware Item", command=self.add_item, bg=SUCCESS_GREEN, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2").grid(row=2, column=0, columnspan=4, sticky="we", padx=10, pady=5)

            edit_frame = ttk.LabelFrame(self.tab_catalog, text=" Admin Controls - Edit Checked Component ")
            edit_frame.pack(fill="x", pady=(0, 5))

            tk.Label(edit_frame, text="New Quantity:", bg=BG_MAIN, fg=TEXT_MAIN).grid(row=0, column=0, padx=10, pady=5, sticky="e")
            self.entry_upd_qty = tk.Entry(edit_frame, width=18, **entry_cfg)
            self.entry_upd_qty.grid(row=0, column=1, pady=5, ipady=3)

            tk.Label(edit_frame, text="New Unit Price (₱):", bg=BG_MAIN, fg=TEXT_MAIN).grid(row=0, column=2, padx=10, pady=5, sticky="e")
            self.entry_upd_price = tk.Entry(edit_frame, width=18, **entry_cfg)
            self.entry_upd_price.grid(row=0, column=3, pady=5, ipady=3)

            tk.Button(edit_frame, text="Update Checked Component", command=self.update_item, bg=ACCENT_CYAN, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2").grid(row=0, column=4, sticky="we", padx=20, pady=5, ipadx=10)

        grid_frame = tk.Frame(self.tab_catalog, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        grid_frame.pack(fill="both", expand=True, pady=5)

        self.tree = ttk.Treeview(grid_frame, columns=("Select", "ID", "Name", "Category", "Qty", "Price"), show="headings", selectmode="none")
        self.tree.bind("<ButtonRelease-1>", self.toggle_check)

        headers = [("Select", "[ ✔ ]", 50), ("ID", "ID", 50), ("Name", "Name", 250),
                   ("Category", "Category", 150), ("Qty", "Qty", 100), ("Price", "Price", 150)]

        for col, txt, width in headers:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=width, anchor="center")

        self.tree.tag_configure("no_stock", background=TINT_DANGER, foreground=DANGER_RED)
        self.tree.tag_configure("low_stock", background=TINT_WARN, foreground=ACCENT_AMBER)
        self.tree.tag_configure("in_stock", background=TINT_SUCCESS, foreground=SUCCESS_GREEN)
        self.tree.tag_configure("normal", background=BG_CARD, foreground=TEXT_MAIN)

        scroll_y = ttk.Scrollbar(grid_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        action_frame = tk.Frame(self.tab_catalog, bg=BG_MAIN)
        action_frame.pack(fill="x", pady=(5, 0))

        if self.role == "ADMIN":
            tk.Button(action_frame, text="🗑 Delete Selected (✔)", command=self.delete_item, bg=DANGER_RED, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", padx=15, pady=2).pack(side="left")

            tk.Button(action_frame, text="Export Inventory to CSV Report", command=self.export_csv, bg=BTN_PURPLE, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", pady=2).pack(side="left", fill="x", expand=True, padx=(10, 0))

        tk.Button(action_frame, text="Change Password", command=self.change_password, bg=ACCENT_CYAN, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", pady=2, padx=20).pack(side="right")

    def build_dashboard_tab(self):
        kpi_frame = tk.Frame(self.tab_dashboard, bg=BG_MAIN)
        kpi_frame.pack(fill="x", pady=10, padx=10)

        self.kpi_labels = {}
        kpi_defs = [
            ("total_items", "Total Items"),
            ("total_valuation", "Total Valuation"),
            ("low_stock", "Low Stock"),
            ("out_of_stock", "Out of Stock"),
            ("active_borrows", "Active Borrows"),
            ("overdue", "Overdue Returns"),
            ("missing", "Missing / Not Returned"),
        ]
        for key, label in kpi_defs:
            card = tk.Frame(kpi_frame, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
            card.pack(side="left", expand=True, fill="both", padx=5)
            tk.Label(card, text=label, font=FONT_MAIN, bg=BG_CARD, fg=TEXT_MUTED).pack(pady=(10, 0))
            val_lbl = tk.Label(card, text="0", font=("Segoe UI", 16, "bold"), bg=BG_CARD, fg=ACCENT_CYAN)
            val_lbl.pack(pady=(0, 10))
            self.kpi_labels[key] = val_lbl

        self.chart_container = tk.Frame(self.tab_dashboard, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        self.chart_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tk.Button(self.tab_dashboard, text="Refresh Dashboard", command=self.refresh_dashboard, bg=ACCENT_CYAN, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2").pack(pady=(0, 10))

    def refresh_dashboard(self):
        conn = sqlite3.connect("hardware_inventory.db")
        check_missing_borrows(conn)
        rows = conn.execute("SELECT category, quantity, unit_price FROM hardware").fetchall()

        total_items = len(rows)
        total_valuation = sum(q * p for _, q, p in rows)
        low_stock = sum(1 for _, q, _ in rows if 1 <= q <= 9)
        out_of_stock = sum(1 for _, q, _ in rows if q == 0)

        active = conn.execute("SELECT COUNT(*) FROM borrow_requests WHERE status='APPROVED'").fetchone()[0]
        overdue = conn.execute("SELECT COUNT(*) FROM borrow_requests WHERE status='APPROVED' AND due_date < ?", (today_str(),)).fetchone()[0]
        missing = conn.execute("SELECT COUNT(*) FROM borrow_requests WHERE status='MISSING'").fetchone()[0]

        category_totals = {}
        for cat, qty, _ in rows:
            category_totals[cat] = category_totals.get(cat, 0) + qty
        conn.close()

        self.kpi_labels["total_items"].config(text=str(total_items))
        self.kpi_labels["total_valuation"].config(text=f"₱{total_valuation:,.2f}")
        self.kpi_labels["low_stock"].config(text=str(low_stock))
        self.kpi_labels["out_of_stock"].config(text=str(out_of_stock))
        self.kpi_labels["active_borrows"].config(text=str(active))
        overdue_color = DANGER_RED if overdue > 0 else SUCCESS_GREEN
        self.kpi_labels["overdue"].config(text=str(overdue), fg=overdue_color)
        missing_color = DANGER_STRONG if missing > 0 else SUCCESS_GREEN
        self.kpi_labels["missing"].config(text=str(missing), fg=missing_color)

        for widget in self.chart_container.winfo_children():
            widget.destroy()

        if not MATPLOTLIB_AVAILABLE:
            tk.Label(self.chart_container, text="Install matplotlib to view the stock-by-category chart (pip install matplotlib)", bg=BG_CARD, fg=TEXT_MUTED, font=FONT_MAIN).pack(expand=True)
            return

        if not category_totals:
            tk.Label(self.chart_container, text="No inventory data to chart yet.", bg=BG_CARD, fg=TEXT_MUTED, font=FONT_MAIN).pack(expand=True)
            return

        fig = Figure(figsize=(8, 4), dpi=100, facecolor=BG_CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG_CARD)
        cats = list(category_totals.keys())
        vals = list(category_totals.values())
        ax.bar(cats, vals, color=ACCENT_CYAN)
        ax.set_title("Stock Quantity by Category", color=TEXT_MAIN)
        ax.tick_params(colors=TEXT_MAIN, labelrotation=20)
        for spine in ax.spines.values():
            spine.set_color(BORDER)

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def build_borrow_tab(self):
        entry_cfg = {"font": FONT_MAIN, "bg": BG_CARD, "fg": ACCENT_CYAN, "insertbackground": ACCENT_CYAN, "relief": "flat", "highlightthickness": 1, "highlightbackground": BORDER, "highlightcolor": ACCENT_CYAN}

        request_frame = ttk.LabelFrame(self.tab_borrow, text=" Request to Borrow Equipment ")
        request_frame.pack(fill="x", pady=(0, 10))

        tk.Label(request_frame, text="Item:", bg=BG_MAIN, fg=TEXT_MAIN).grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.combo_borrow_item = ttk.Combobox(request_frame, state="readonly", font=FONT_MAIN, width=32)
        self.combo_borrow_item.grid(row=0, column=1, pady=5, ipady=3)

        tk.Label(request_frame, text="Quantity:", bg=BG_MAIN, fg=TEXT_MAIN).grid(row=0, column=2, padx=10, pady=5, sticky="e")
        self.entry_borrow_qty = tk.Entry(request_frame, width=10, **entry_cfg)
        self.entry_borrow_qty.grid(row=0, column=3, pady=5, ipady=3)

        tk.Label(request_frame, text="Due Date (YYYY-MM-DD):", bg=BG_MAIN, fg=TEXT_MAIN).grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_due_date = tk.Entry(request_frame, width=20, **entry_cfg)
        self.entry_due_date.grid(row=1, column=1, pady=5, ipady=3, sticky="w")

        tk.Button(request_frame, text="Submit Borrow Request", command=self.submit_borrow_request, bg=SUCCESS_GREEN, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2").grid(row=1, column=3, sticky="we", padx=10, pady=5)

        list_frame = ttk.LabelFrame(self.tab_borrow, text=" Borrow History ")
        list_frame.pack(fill="both", expand=True)

        cols = ("Select", "ID", "Item", "Qty", "Requested", "Due", "Status")
        self.borrow_tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="none")
        self.borrow_tree.bind("<ButtonRelease-1>", self.toggle_borrow_check)

        widths = [50, 50, 220, 60, 110, 110, 110]
        for col, width in zip(cols, widths):
            self.borrow_tree.heading(col, text=col)
            self.borrow_tree.column(col, width=width, anchor="center")

        self.borrow_tree.tag_configure("pending", background=TINT_WARN, foreground=ACCENT_AMBER)
        self.borrow_tree.tag_configure("approved", background=TINT_SUCCESS, foreground=SUCCESS_GREEN)
        self.borrow_tree.tag_configure("overdue", background=TINT_DANGER, foreground=DANGER_RED)
        self.borrow_tree.tag_configure("missing", background=TINT_DANGER, foreground=DANGER_STRONG)
        self.borrow_tree.tag_configure("returned", background=BG_CARD, foreground=TEXT_MAIN)
        self.borrow_tree.tag_configure("rejected", background=BG_CARD, foreground=TEXT_MUTED)

        scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.borrow_tree.yview)
        self.borrow_tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self.borrow_tree.pack(side="left", fill="both", expand=True)

        action_frame = tk.Frame(self.tab_borrow, bg=BG_MAIN)
        action_frame.pack(fill="x", pady=(5, 0))
        tk.Button(action_frame, text="Return Checked Item", command=self.return_borrowed_item, bg=ACCENT_AMBER, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", padx=15, pady=2).pack(side="left")

    def refresh_borrow_item_choices(self):
        conn = sqlite3.connect("hardware_inventory.db")
        rows = conn.execute("SELECT item_id, item_name, quantity FROM hardware WHERE quantity > 0").fetchall()
        conn.close()
        self.borrow_item_map = {f"{name} (Available: {qty})": item_id for item_id, name, qty in rows}
        self.combo_borrow_item["values"] = list(self.borrow_item_map.keys())

    def submit_borrow_request(self):
        self.refresh_borrow_item_choices()
        choice = self.combo_borrow_item.get()
        qty_str = self.entry_borrow_qty.get().strip()
        due = self.entry_due_date.get().strip()

        if not choice or choice not in self.borrow_item_map:
            return messagebox.showwarning("Error", "Select a valid item.")
        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            return messagebox.showerror("Error", "Quantity must be a positive whole number.")
        try:
            due_date_obj = datetime.strptime(due, "%Y-%m-%d").date()
            if due_date_obj < date.today():
                return messagebox.showerror("Error", "Due date cannot be in the past.")
        except ValueError:
            return messagebox.showerror("Error", "Due date must be in YYYY-MM-DD format.")

        item_id = self.borrow_item_map[choice]
        conn = sqlite3.connect("hardware_inventory.db")
        available = conn.execute("SELECT quantity FROM hardware WHERE item_id=?", (item_id,)).fetchone()[0]
        if qty > available:
            conn.close()
            return messagebox.showwarning("Insufficient Stock", f"Only {available} unit(s) currently available.")

        conn.execute("INSERT INTO borrow_requests (item_id, username, quantity, request_date, due_date, status) VALUES (?, ?, ?, ?, ?, 'PENDING')",
                     (item_id, self.username, qty, today_str(), due))
        conn.commit()
        conn.close()
        logging.info(f"{self.username} requested to borrow item ID {item_id} (qty {qty}) due {due}.")
        messagebox.showinfo("Submitted", "Borrow request submitted for admin approval.")

        self.entry_borrow_qty.delete(0, tk.END)
        self.entry_due_date.delete(0, tk.END)
        self.combo_borrow_item.set("")
        self.load_borrow_data()

    def toggle_borrow_check(self, event):
        region = self.borrow_tree.identify_region(event.x, event.y)
        if region == "cell":
            col = self.borrow_tree.identify_column(event.x)
            if col == "#1":
                item = self.borrow_tree.identify_row(event.y)
                if item:
                    vals = list(self.borrow_tree.item(item, "values"))
                    vals[0] = CHECK_FILLED if vals[0] == CHECK_EMPTY else CHECK_EMPTY
                    self.borrow_tree.item(item, values=vals)

    def load_borrow_data(self):
        self.refresh_borrow_item_choices()
        for row in self.borrow_tree.get_children():
            self.borrow_tree.delete(row)

        conn = sqlite3.connect("hardware_inventory.db")
        check_missing_borrows(conn)
        if self.role == "ADMIN":
            rows = conn.execute("""
                SELECT br.request_id, h.item_name, br.quantity, br.request_date, br.due_date, br.status
                FROM borrow_requests br JOIN hardware h ON br.item_id = h.item_id
                ORDER BY br.request_id DESC
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT br.request_id, h.item_name, br.quantity, br.request_date, br.due_date, br.status
                FROM borrow_requests br JOIN hardware h ON br.item_id = h.item_id
                WHERE br.username = ?
                ORDER BY br.request_id DESC
            """, (self.username,)).fetchall()
        conn.close()

        today = today_str()
        for req_id, item_name, qty, req_date, due, status in rows:
            if status == "MISSING":
                tag = "missing"
            elif status == "APPROVED" and due < today:
                tag = "overdue"
            elif status == "APPROVED":
                tag = "approved"
            elif status == "PENDING":
                tag = "pending"
            elif status == "RETURNED":
                tag = "returned"
            else:
                tag = "rejected"
            self.borrow_tree.insert("", tk.END, values=(CHECK_EMPTY, req_id, item_name, qty, req_date, due, status), tags=(tag,))

    def return_borrowed_item(self):
        checked = [i for i in self.borrow_tree.get_children() if self.borrow_tree.item(i, "values")[0] == CHECK_FILLED]
        if not checked:
            return messagebox.showwarning("Selection Error", "Check the item(s) you are returning.")

        conn = sqlite3.connect("hardware_inventory.db")
        returned_count = 0
        for row in checked:
            vals = self.borrow_tree.item(row, "values")
            req_id, status = vals[1], vals[6]
            if status not in ("APPROVED", "MISSING"):
                continue
            record = conn.execute("SELECT item_id, quantity, username FROM borrow_requests WHERE request_id=?", (req_id,)).fetchone()
            if not record:
                continue
            item_id, qty, owner = record
            if self.role != "ADMIN" and owner != self.username:
                continue
            conn.execute("UPDATE borrow_requests SET status='RETURNED', return_date=? WHERE request_id=?", (today_str(), req_id))
            conn.execute("UPDATE hardware SET quantity = quantity + ? WHERE item_id=?", (qty, item_id))
            sync_hardware_status(conn, item_id)
            logging.info(f"{self.username} returned borrowed item ID {item_id} (qty {qty}), request #{req_id}.")
            returned_count += 1
        conn.commit()
        conn.close()

        if returned_count == 0:
            messagebox.showinfo("Nothing to Return", "No eligible approved borrow records were checked.")
        else:
            messagebox.showinfo("Returned", f"{returned_count} item(s) marked as returned.")

        self.load_borrow_data()
        self.load_data()
        self.refresh_dashboard()

    def build_approvals_tab(self):
        content = tk.Frame(self.tab_approvals, bg=BG_MAIN)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(content, text="PENDING APPROVALS", font=("Segoe UI", 16, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(pady=(0, 10))

        cols = ("Select", "ID", "Type", "Requester", "Details", "Status")
        self.approvals_tree = ttk.Treeview(content, columns=cols, show="headings", selectmode="none")
        self.approvals_tree.bind("<ButtonRelease-1>", self.toggle_approval_check)

        widths = [50, 50, 90, 130, 320, 90]
        for col, width in zip(cols, widths):
            self.approvals_tree.heading(col, text=col)
            self.approvals_tree.column(col, width=width, anchor="center")

        self.approvals_tree.tag_configure("reset", background=BG_PANEL, foreground=TEXT_MAIN)
        self.approvals_tree.tag_configure("borrow", background=BG_CARD, foreground=TEXT_MAIN)

        scroll_y = ttk.Scrollbar(content, orient="vertical", command=self.approvals_tree.yview)
        self.approvals_tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self.approvals_tree.pack(fill="both", expand=True)

        btn_frame = tk.Frame(self.tab_approvals, bg=BG_MAIN)
        btn_frame.pack(fill="x", pady=10)
        tk.Button(btn_frame, text="Approve Checked", command=lambda: self.process_approvals("APPROVE"), bg=SUCCESS_GREEN, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", padx=15, pady=5).pack(side="left")
        tk.Button(btn_frame, text="Reject Checked", command=lambda: self.process_approvals("REJECT"), bg=DANGER_RED, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", padx=15, pady=5).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Refresh", command=self.load_approvals, bg=ACCENT_CYAN, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", padx=15, pady=5).pack(side="right")

    def toggle_approval_check(self, event):
        region = self.approvals_tree.identify_region(event.x, event.y)
        if region == "cell":
            col = self.approvals_tree.identify_column(event.x)
            if col == "#1":
                item = self.approvals_tree.identify_row(event.y)
                if item:
                    vals = list(self.approvals_tree.item(item, "values"))
                    vals[0] = CHECK_FILLED if vals[0] == CHECK_EMPTY else CHECK_EMPTY
                    self.approvals_tree.item(item, values=vals)

    def load_approvals(self):
        for row in self.approvals_tree.get_children():
            self.approvals_tree.delete(row)

        conn = sqlite3.connect("hardware_inventory.db")
        resets = conn.execute("SELECT request_id, username, email FROM reset_requests WHERE status='PENDING'").fetchall()
        for req_id, user, email in resets:
            details = f"Reset account for {user} ({email})"
            self.approvals_tree.insert("", tk.END, values=(CHECK_EMPTY, req_id, "RESET", user, details, "PENDING"), tags=("reset",))

        borrows = conn.execute("""
            SELECT br.request_id, br.username, h.item_name, br.quantity, br.due_date
            FROM borrow_requests br JOIN hardware h ON br.item_id = h.item_id
            WHERE br.status='PENDING'
        """).fetchall()
        for req_id, user, item_name, qty, due in borrows:
            details = f"Borrow {qty}x {item_name}, due {due}"
            self.approvals_tree.insert("", tk.END, values=(CHECK_EMPTY, req_id, "BORROW", user, details, "PENDING"), tags=("borrow",))
        conn.close()

    def process_approvals(self, action):
        checked = [i for i in self.approvals_tree.get_children() if self.approvals_tree.item(i, "values")[0] == CHECK_FILLED]
        if not checked:
            return messagebox.showwarning("Selection Error", "Check at least one request.")

        conn = sqlite3.connect("hardware_inventory.db")
        processed = 0
        skipped = 0
        for row in checked:
            vals = self.approvals_tree.item(row, "values")
            req_id, req_type, user = vals[1], vals[2], vals[3]

            if req_type == "RESET":
                if action == "APPROVE":
                    conn.execute("UPDATE users SET status='ACTIVE', password=? WHERE username=?", (hash_password("Password123!"), user))
                    conn.execute("UPDATE reset_requests SET status='APPROVED' WHERE request_id=?", (req_id,))
                    logging.info(f"Admin {self.username} approved account unlock for {user}.")
                else:
                    conn.execute("UPDATE reset_requests SET status='REJECTED' WHERE request_id=?", (req_id,))
                    logging.info(f"Admin {self.username} rejected reset request for {user}.")
                processed += 1

            elif req_type == "BORROW":
                if action == "APPROVE":
                    record = conn.execute("SELECT item_id, quantity FROM borrow_requests WHERE request_id=?", (req_id,)).fetchone()
                    item_id, qty = record
                    available = conn.execute("SELECT quantity FROM hardware WHERE item_id=?", (item_id,)).fetchone()[0]
                    if qty > available:
                        skipped += 1
                        continue
                    conn.execute("UPDATE hardware SET quantity = quantity - ? WHERE item_id=?", (qty, item_id))
                    sync_hardware_status(conn, item_id)
                    conn.execute("UPDATE borrow_requests SET status='APPROVED' WHERE request_id=?", (req_id,))
                    logging.info(f"Admin {self.username} approved borrow request #{req_id} for {user}.")
                else:
                    conn.execute("UPDATE borrow_requests SET status='REJECTED' WHERE request_id=?", (req_id,))
                    logging.info(f"Admin {self.username} rejected borrow request #{req_id} for {user}.")
                processed += 1

        conn.commit()
        conn.close()

        if skipped:
            messagebox.showwarning("Some Skipped", f"{skipped} borrow request(s) skipped due to insufficient stock.")
        if processed:
            messagebox.showinfo("Done", f"{processed} request(s) processed.")

        self.load_approvals()
        self.load_data()
        self.load_borrow_data()
        self.refresh_dashboard()

    def build_logs_tab(self):
        control_frame = tk.Frame(self.tab_logs, bg=BG_MAIN)
        control_frame.pack(fill="x", pady=(0, 10))

        tk.Label(control_frame, text="Search:", bg=BG_MAIN, fg=TEXT_MAIN).pack(side="left", padx=(0, 5))
        self.log_search_var = tk.StringVar()
        tk.Entry(control_frame, textvariable=self.log_search_var, width=30, font=FONT_MAIN, bg=BG_CARD, fg=ACCENT_CYAN, insertbackground=ACCENT_CYAN, relief="flat", highlightthickness=1, highlightbackground=BORDER).pack(side="left", ipady=3)

        tk.Label(control_frame, text="Level:", bg=BG_MAIN, fg=TEXT_MAIN).pack(side="left", padx=(15, 5))
        self.log_level_var = tk.StringVar(value="ALL")
        level_combo = ttk.Combobox(control_frame, textvariable=self.log_level_var, values=["ALL", "INFO", "WARNING", "ERROR"], state="readonly", font=FONT_MAIN, width=10)
        level_combo.pack(side="left", ipady=3)

        tk.Button(control_frame, text="Refresh Logs", command=self.refresh_logs, bg=ACCENT_CYAN, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", padx=15).pack(side="left", padx=15)
        tk.Button(control_frame, text="Export Logs to CSV", command=self.export_logs_csv, bg=BTN_PURPLE, fg=BTN_FG, font=FONT_BOLD, relief="flat", cursor="hand2", padx=15).pack(side="left")

        log_frame = tk.Frame(self.tab_logs, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_frame, bg=BG_LOG, fg=TEXT_MAIN, font=("Consolas", 9), wrap="none", relief="flat")
        scroll_y = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        self.log_search_var.trace("w", lambda *args: self.refresh_logs())
        level_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_logs())

    def refresh_logs(self):
        self.log_text.delete("1.0", tk.END)
        log_path = "app_logging/app.log"
        if not os.path.exists(log_path):
            self.log_text.insert(tk.END, "No log entries yet.")
            return

        with open(log_path, "r") as f:
            lines = f.readlines()

        search = self.log_search_var.get().lower().strip()
        level = self.log_level_var.get()

        filtered = []
        for line in lines[-1000:]:
            if level != "ALL" and f" - {level} - " not in line:
                continue
            if search and search not in line.lower():
                continue
            filtered.append(line)

        if not filtered:
            self.log_text.insert(tk.END, "No matching log entries.")
            return

        for line in filtered:
            self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)

    def export_logs_csv(self):
        log_path = "app_logging/app.log"
        if not os.path.exists(log_path):
            return messagebox.showinfo("No Data", "No logs to export yet.")

        with open(log_path, "r") as f:
            lines = f.readlines()

        with open("system_logs_export.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Level", "Message"])
            for line in lines:
                parts = line.strip().split(" - ", 2)
                if len(parts) == 3:
                    writer.writerow(parts)
                else:
                    writer.writerow(["", "", line.strip()])

        logging.info(f"{self.username} exported system logs to CSV.")
        messagebox.showinfo("Export Complete", "Logs exported to system_logs_export.csv")

    def logout(self):
        logging.info(f"{self.username} logged out.")
        self.master.destroy()
        auth_root = tk.Tk()
        app = AuthWindow(auth_root)
        auth_root.mainloop()

    def toggle_check(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            col = self.tree.identify_column(event.x)
            if col == "#1":
                item = self.tree.identify_row(event.y)
                if item:
                    vals = list(self.tree.item(item, "values"))
                    vals[0] = CHECK_FILLED if vals[0] == CHECK_EMPTY else CHECK_EMPTY
                    self.tree.item(item, values=vals)

    def load_data(self):
        for row in self.tree.get_children(): self.tree.delete(row)
        conn = sqlite3.connect("hardware_inventory.db")
        search_query = f"%{self.search_var.get()}%"
        cat_query = self.cat_filter_var.get()

        if cat_query == "ALL":
            rows = conn.execute("SELECT * FROM hardware WHERE item_name LIKE ?", (search_query,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM hardware WHERE item_name LIKE ? AND category = ?", (search_query, cat_query)).fetchall()

        total_valuation = 0.0
        for row in rows:
            qty, price = row[3], row[4]
            total_valuation += (qty * price)

            if qty == 0:
                tag = "no_stock"
            elif qty <= 9:
                tag = "low_stock"
            else:
                tag = "in_stock"

            self.tree.insert("", tk.END, values=(CHECK_EMPTY, row[0], row[1], row[2], row[3], row[4]), tags=(tag,))

        conn.close()
        self.lbl_valuation.config(text=f"Total Asset Valuation: ₱{total_valuation:,.2f}")

    def check_duplicate_name(self, event=None):
        name = self.entry_name.get().strip()
        if not name:
            self.entry_name.config(bg=BG_CARD, fg=ACCENT_CYAN)
            return

        conn = sqlite3.connect("hardware_inventory.db")
        existing_item = conn.execute("SELECT item_name FROM hardware WHERE LOWER(item_name) = LOWER(?)", (name,)).fetchone()
        conn.close()

        if existing_item:
            self.entry_name.config(bg=TINT_DANGER, fg=DANGER_STRONG)
        else:
            self.entry_name.config(bg=BG_CARD, fg=ACCENT_CYAN)

    def add_item(self):
        try:
            name, cat = self.entry_name.get().strip(), self.combo_add_cat.get().strip()
            qty, price = int(self.entry_qty.get()), float(self.entry_price.get())
            if not name or not cat: return messagebox.showwarning("Error", "Name and Category required.")

            conn = sqlite3.connect("hardware_inventory.db")
            existing_item = conn.execute("SELECT item_name FROM hardware WHERE LOWER(item_name) = LOWER(?)", (name,)).fetchone()
            if existing_item:
                conn.close()
                self.entry_name.config(bg=TINT_DANGER, fg=DANGER_STRONG)
                return messagebox.showwarning("Duplicate Item", f"The item '{name}' is already in the inventory!")

            conn.execute("INSERT INTO hardware (item_name, category, quantity, unit_price, status) VALUES (?, ?, ?, ?, ?)",
                         (name, cat, qty, price, calculate_status(qty)))
            conn.commit()
            conn.close()
            logging.info(f"{self.username} added inventory item: {name}")

            self.entry_name.delete(0, tk.END)
            self.entry_name.config(bg=BG_CARD, fg=ACCENT_CYAN)
            self.combo_add_cat.current(0)
            self.entry_qty.delete(0, tk.END)
            self.entry_price.delete(0, tk.END)
            self.load_data()
        except ValueError:
            messagebox.showerror("Error", "Numeric values required for Qty and Price.")

    def update_item(self):
        checked = [i for i in self.tree.get_children() if self.tree.item(i, "values")[0] == CHECK_FILLED]

        if not checked:
            return messagebox.showwarning("Selection Error", "Please check a box to update!")
        if len(checked) > 1:
            return messagebox.showwarning("Selection Error", "Please check only ONE item to update!")

        item_id = self.tree.item(checked[0], "values")[1]
        qty_str = self.entry_upd_qty.get().strip()
        price_str = self.entry_upd_price.get().strip()

        if not qty_str or not price_str:
            return messagebox.showwarning("Input Error", "Please fill in both New Qty and New Price to update.")

        try:
            new_qty = int(qty_str)
            new_price = float(price_str)
        except ValueError:
            return messagebox.showwarning("Input Error", "Quantity must be a whole number and Price must be a number.")

        new_status = calculate_status(new_qty)

        conn = sqlite3.connect("hardware_inventory.db")
        conn.execute("UPDATE hardware SET quantity = ?, unit_price = ?, status = ? WHERE item_id = ?",
                     (new_qty, new_price, new_status, item_id))
        conn.commit()
        conn.close()
        logging.info(f"{self.username} updated inventory item ID {item_id}")

        self.entry_upd_qty.delete(0, tk.END)
        self.entry_upd_price.delete(0, tk.END)

        self.load_data()
        messagebox.showinfo("Success", "Hardware item updated successfully!")

    def delete_item(self):
        checked = [i for i in self.tree.get_children() if self.tree.item(i, "values")[0] == CHECK_FILLED]
        if not checked: return messagebox.showwarning("Warning", "Please select items using the checkmarks.")
        if messagebox.askyesno("Confirm", f"Delete {len(checked)} hardware components?"):
            conn = sqlite3.connect("hardware_inventory.db")
            for item in checked:
                conn.execute("DELETE FROM hardware WHERE item_id=?", (self.tree.item(item, "values")[1],))
            conn.commit()
            conn.close()
            logging.info(f"{self.username} deleted {len(checked)} inventory item(s).")
            self.load_data()

    def export_csv(self):
        conn = sqlite3.connect("hardware_inventory.db")
        rows = conn.execute("SELECT item_id, item_name, category, quantity, unit_price FROM hardware").fetchall()
        with open('inventory.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Category", "Qty", "Price"])
            writer.writerows(rows)
        conn.close()
        logging.info(f"{self.username} exported inventory to CSV.")
        messagebox.showinfo("Export Complete", "Data extracted to inventory.csv")

    def change_password(self):
        new_pw = ask_password_with_toggle(self.master, "Change Password", "Enter new passcode:")
        if new_pw:
            conn = sqlite3.connect("hardware_inventory.db")
            conn.execute("UPDATE users SET password = ? WHERE username = ?", (hash_password(new_pw), self.username))
            conn.commit()
            conn.close()
            logging.info(f"{self.username} updated their profile password.")
            messagebox.showinfo("Success", "Security key updated.")

def launch_main(username, role):
    root = tk.Tk()
    app = InventoryApp(root, username, role)
    root.mainloop()

if __name__ == "__main__":
    init_db()
    auth_root = tk.Tk()
    app = AuthWindow(auth_root)
    auth_root.mainloop()