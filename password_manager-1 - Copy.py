"""
Password Manager in Python
===========================
Securely stores, retrieves, and manages passwords using:
  - Master password protected vault
  - AES-256 encryption via Fernet (symmetric key derived from master password)
  - PBKDF2-HMAC-SHA256 key derivation (100,000 iterations)
  - SQLite database for persistent storage
  - Strong password generator
  - Password strength checker

Author : Debasish Parida
Project: Python Internship — Password Manager

Requirements:
    pip install cryptography

Usage:
    python password_manager.py
    python password_manager.py --demo
"""

import os
import sys
import sqlite3
import secrets
import string
import hashlib
import base64
import getpass
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Force UTF-8 output so emoji characters (🔐 ✅ ❌ etc.) print
# correctly in BOTH IDLE and VS Code's terminal on Windows.
# Windows consoles often default to cp1252, which crashes on
# emoji with a UnicodeEncodeError.
# ─────────────────────────────────────────────────────────────
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

# ── Third-party (install once) ──────────────────────────────
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
except ImportError:
    print("\n  ❌  Missing dependency. Run:  pip install cryptography\n")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
DB_FILE   = "vault.db"
SALT_FILE = "vault.salt"
ITERATIONS = 100_000          # PBKDF2 iterations (NIST recommended)
KEY_LENGTH = 32               # bytes → 256-bit key

# ─────────────────────────────────────────────────────────────
# KEY DERIVATION  (Master Password → Fernet key)
# ─────────────────────────────────────────────────────────────

def _load_or_create_salt() -> bytes:
    """Load existing salt or generate a new one."""
    if Path(SALT_FILE).exists():
        return Path(SALT_FILE).read_bytes()
    salt = os.urandom(16)
    Path(SALT_FILE).write_bytes(salt)
    return salt


def derive_key(master_password: str) -> bytes:
    """Derive a 256-bit Fernet-compatible key from the master password."""
    salt = _load_or_create_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=ITERATIONS,
    )
    raw_key = kdf.derive(master_password.encode())
    return base64.urlsafe_b64encode(raw_key)   # Fernet needs url-safe base64


def get_fernet(master_password: str) -> Fernet:
    return Fernet(derive_key(master_password))


# ─────────────────────────────────────────────────────────────
# ENCRYPTION / DECRYPTION
# ─────────────────────────────────────────────────────────────

def encrypt(text: str, fernet: Fernet) -> str:
    return fernet.encrypt(text.encode()).decode()


def decrypt(token: str, fernet: Fernet) -> str:
    return fernet.decrypt(token.encode()).decode()


# ─────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────

def init_db() -> sqlite3.Connection:
    """Create (or open) the SQLite vault and ensure tables exist."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vault (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            site        TEXT    NOT NULL,
            username    TEXT    NOT NULL,
            password    TEXT    NOT NULL,   -- encrypted
            notes       TEXT    DEFAULT '',
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        )
    """)
    # Master-password verifier row (stores a known encrypted token)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def _set_master_verifier(conn: sqlite3.Connection, fernet: Fernet) -> None:
    """Store an encrypted sentinel so we can verify the master password later."""
    token = encrypt("VAULT_OK", fernet)
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("verifier", token)
    )
    conn.commit()


def verify_master(conn: sqlite3.Connection, fernet: Fernet) -> bool:
    """Return True if the master password decrypts the verifier correctly."""
    row = conn.execute(
        "SELECT value FROM meta WHERE key = 'verifier'"
    ).fetchone()
    if not row:
        return True   # first run — no verifier yet
    try:
        result = decrypt(row[0], fernet)
        return result == "VAULT_OK"
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# PASSWORD GENERATOR
# ─────────────────────────────────────────────────────────────

def generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """
    Generate a cryptographically secure random password.
    Guarantees at least one character from each enabled group.
    """
    pool = string.ascii_lowercase
    required: list[str] = [secrets.choice(string.ascii_lowercase)]

    if use_upper:
        pool += string.ascii_uppercase
        required.append(secrets.choice(string.ascii_uppercase))
    if use_digits:
        pool += string.digits
        required.append(secrets.choice(string.digits))
    if use_symbols:
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        pool += symbols
        required.append(secrets.choice(symbols))

    remaining = [secrets.choice(pool) for _ in range(length - len(required))]
    password_list = required + remaining
    secrets.SystemRandom().shuffle(password_list)
    return "".join(password_list)


# ─────────────────────────────────────────────────────────────
# PASSWORD STRENGTH CHECKER
# ─────────────────────────────────────────────────────────────

def check_strength(password: str) -> tuple[str, list[str]]:
    """
    Return (rating, tips).
    Rating: 'Weak' | 'Fair' | 'Strong' | 'Very Strong'
    """
    score = 0
    tips: list[str] = []

    if len(password) >= 12:
        score += 1
    else:
        tips.append("Use at least 12 characters")

    if len(password) >= 16:
        score += 1

    if any(c.isupper() for c in password):
        score += 1
    else:
        tips.append("Add uppercase letters (A-Z)")

    if any(c.islower() for c in password):
        score += 1
    else:
        tips.append("Add lowercase letters (a-z)")

    if any(c.isdigit() for c in password):
        score += 1
    else:
        tips.append("Add digits (0-9)")

    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1
    else:
        tips.append("Add symbols (!@#$…)")

    rating = (
        "Very Strong" if score >= 6 else
        "Strong"      if score >= 4 else
        "Fair"        if score >= 3 else
        "Weak"
    )
    return rating, tips


# ─────────────────────────────────────────────────────────────
# VAULT OPERATIONS
# ─────────────────────────────────────────────────────────────

def add_entry(conn, fernet, site, username, password, notes="") -> int:
    now = datetime.now().isoformat(timespec="seconds")
    enc_password = encrypt(password, fernet)
    enc_notes    = encrypt(notes, fernet) if notes else ""
    cur = conn.execute(
        """INSERT INTO vault (site, username, password, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (site, username, enc_password, enc_notes, now, now)
    )
    conn.commit()
    return cur.lastrowid


def get_entry(conn, fernet, entry_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, site, username, password, notes, created_at, updated_at FROM vault WHERE id = ?",
        (entry_id,)
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "site": row[1], "username": row[2],
        "password": decrypt(row[3], fernet),
        "notes": decrypt(row[4], fernet) if row[4] else "",
        "created_at": row[5], "updated_at": row[6],
    }


def search_entries(conn, keyword: str) -> list[tuple]:
    """Search by site or username (plain text fields)."""
    keyword = f"%{keyword.lower()}%"
    return conn.execute(
        """SELECT id, site, username, created_at FROM vault
           WHERE LOWER(site) LIKE ? OR LOWER(username) LIKE ?
           ORDER BY site""",
        (keyword, keyword)
    ).fetchall()


def list_entries(conn) -> list[tuple]:
    return conn.execute(
        "SELECT id, site, username, created_at FROM vault ORDER BY site"
    ).fetchall()


def update_entry(conn, fernet, entry_id: int, password: str, notes: str = "") -> bool:
    now = datetime.now().isoformat(timespec="seconds")
    enc_password = encrypt(password, fernet)
    enc_notes    = encrypt(notes, fernet) if notes else ""
    rowcount = conn.execute(
        "UPDATE vault SET password = ?, notes = ?, updated_at = ? WHERE id = ?",
        (enc_password, enc_notes, now, entry_id)
    ).rowcount
    conn.commit()
    return rowcount > 0


def delete_entry(conn, entry_id: int) -> bool:
    rowcount = conn.execute("DELETE FROM vault WHERE id = ?", (entry_id,)).rowcount
    conn.commit()
    return rowcount > 0


# ─────────────────────────────────────────────────────────────
# CLI DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────

DIVIDER  = "  " + "─" * 55
DIVIDER2 = "  " + "═" * 55

def print_header(title: str) -> None:
    print(f"\n{DIVIDER2}")
    print(f"  🔐  {title}")
    print(DIVIDER2)


def print_row(entries: list[tuple]) -> None:
    if not entries:
        print("  (no entries found)")
        return
    print(f"\n  {'ID':<5} {'Site':<25} {'Username':<25} {'Saved On'}")
    print(DIVIDER)
    for row in entries:
        print(f"  {row[0]:<5} {row[1]:<25} {row[2]:<25} {row[3][:10]}")
    print()


def strength_bar(rating: str) -> str:
    bars = {"Weak": "█░░░", "Fair": "██░░", "Strong": "███░", "Very Strong": "████"}
    colors = {"Weak": "🔴", "Fair": "🟡", "Strong": "🟢", "Very Strong": "🟢"}
    return f"{colors.get(rating, '')} {rating} {bars.get(rating, '')}"


# ─────────────────────────────────────────────────────────────
# MASTER PASSWORD SETUP / LOGIN
# ─────────────────────────────────────────────────────────────

def setup_or_login(conn) -> Fernet | None:
    """
    If vault is new → set master password.
    If vault exists → authenticate.
    Returns a Fernet instance or None on failure.
    """
    is_new = not conn.execute(
        "SELECT 1 FROM meta WHERE key = 'verifier'"
    ).fetchone()

    if is_new:
        print("\n  🆕 New vault detected. Set your master password.")
        print("  ⚠️  This password cannot be recovered. Store it safely!\n")
        while True:
            pw  = getpass.getpass("  Create master password: ")
            pw2 = getpass.getpass("  Confirm master password: ")
            if pw != pw2:
                print("  ❌ Passwords don't match. Try again.\n")
                continue
            if len(pw) < 8:
                print("  ❌ Master password must be at least 8 characters.\n")
                continue
            fernet = get_fernet(pw)
            _set_master_verifier(conn, fernet)
            print("\n  ✅ Vault created and locked with your master password.\n")
            return fernet
    else:
        print("\n  🔒 Vault is locked. Enter your master password.")
        for attempt in range(3):
            pw = getpass.getpass("  Master password: ")
            fernet = get_fernet(pw)
            if verify_master(conn, fernet):
                print("  ✅ Vault unlocked.\n")
                return fernet
            remaining = 2 - attempt
            if remaining > 0:
                print(f"  ❌ Wrong password. {remaining} attempt(s) left.\n")
        print("  ❌ Too many failed attempts. Exiting.\n")
        return None


# ─────────────────────────────────────────────────────────────
# MENU ACTIONS
# ─────────────────────────────────────────────────────────────

def action_add(conn, fernet) -> None:
    print_header("Add New Entry")
    site     = input("  Site / App name   : ").strip()
    username = input("  Username / Email  : ").strip()
    if not site or not username:
        print("  ❌ Site and username are required.\n")
        return

    print("\n  Password options:")
    print("  [1] Generate a strong password")
    print("  [2] Enter my own password")
    choice = input("  Choose (1/2): ").strip()

    if choice == "1":
        length_str = input("  Length (default 16): ").strip()
        length = int(length_str) if length_str.isdigit() else 16
        password = generate_password(length)
        rating, tips = check_strength(password)
        print(f"\n  Generated: {password}")
        print(f"  Strength : {strength_bar(rating)}\n")
    else:
        password = getpass.getpass("  Enter password     : ")
        rating, tips = check_strength(password)
        print(f"\n  Strength : {strength_bar(rating)}")
        if tips:
            for tip in tips:
                print(f"    • {tip}")
        print()

    notes = input("  Notes (optional)   : ").strip()
    entry_id = add_entry(conn, fernet, site, username, password, notes)
    print(f"\n  ✅ Saved as entry #{entry_id}\n")


def action_view(conn, fernet) -> None:
    print_header("View Entry")
    id_str = input("  Entry ID to view: ").strip()
    if not id_str.isdigit():
        print("  ❌ Enter a valid numeric ID.\n")
        return
    entry = get_entry(conn, fernet, int(id_str))
    if not entry:
        print(f"  ❌ No entry with ID {id_str}.\n")
        return
    print(f"\n  ID       : {entry['id']}")
    print(f"  Site     : {entry['site']}")
    print(f"  Username : {entry['username']}")
    print(f"  Password : {entry['password']}")
    print(f"  Notes    : {entry['notes'] or '—'}")
    print(f"  Created  : {entry['created_at']}")
    print(f"  Updated  : {entry['updated_at']}\n")


def action_list(conn) -> None:
    print_header("All Entries")
    entries = list_entries(conn)
    print_row(entries)
    print(f"  Total: {len(entries)} entry/entries\n")


def action_search(conn) -> None:
    print_header("Search Entries")
    keyword = input("  Search keyword: ").strip()
    if not keyword:
        print("  ❌ Enter a keyword.\n")
        return
    results = search_entries(conn, keyword)
    print(f"\n  Found {len(results)} result(s) for '{keyword}':")
    print_row(results)


def action_update(conn, fernet) -> None:
    print_header("Update Password")
    id_str = input("  Entry ID to update: ").strip()
    if not id_str.isdigit():
        print("  ❌ Enter a valid numeric ID.\n")
        return
    entry = get_entry(conn, fernet, int(id_str))
    if not entry:
        print(f"  ❌ No entry with ID {id_str}.\n")
        return
    print(f"\n  Updating: {entry['site']} ({entry['username']})")

    print("  [1] Generate new password")
    print("  [2] Enter new password manually")
    choice = input("  Choose (1/2): ").strip()

    if choice == "1":
        length_str = input("  Length (default 16): ").strip()
        length = int(length_str) if length_str.isdigit() else 16
        new_pass = generate_password(length)
        print(f"\n  New password: {new_pass}")
    else:
        new_pass = getpass.getpass("  New password: ")

    rating, _ = check_strength(new_pass)
    print(f"  Strength   : {strength_bar(rating)}")

    notes = input("  New notes (leave blank to keep old): ").strip()
    if not notes:
        notes = entry["notes"]

    ok = update_entry(conn, fernet, int(id_str), new_pass, notes)
    print(f"\n  {'✅ Updated.' if ok else '❌ Update failed.'}\n")


def action_delete(conn) -> None:
    print_header("Delete Entry")
    id_str = input("  Entry ID to delete: ").strip()
    if not id_str.isdigit():
        print("  ❌ Enter a valid numeric ID.\n")
        return
    confirm = input(f"  Delete entry #{id_str}? This cannot be undone. (yes/no): ").strip().lower()
    if confirm != "yes":
        print("  Cancelled.\n")
        return
    ok = delete_entry(conn, int(id_str))
    print(f"\n  {'✅ Deleted.' if ok else '❌ Entry not found.'}\n")


def action_generate() -> None:
    print_header("Password Generator")
    length_str = input("  Length (default 16): ").strip()
    length = int(length_str) if length_str.isdigit() else 16
    symbols = input("  Include symbols? (y/n, default y): ").strip().lower()
    use_sym = symbols != "n"
    pw = generate_password(length, use_symbols=use_sym)
    rating, tips = check_strength(pw)
    print(f"\n  Password : {pw}")
    print(f"  Strength : {strength_bar(rating)}")
    if tips:
        for tip in tips:
            print(f"    • {tip}")
    print()


# ─────────────────────────────────────────────────────────────
# DEMO MODE
# ─────────────────────────────────────────────────────────────

def run_demo() -> None:
    """Create an in-memory vault with sample data and show all features."""
    DEMO_MASTER = "DemoPass@2024"

    # Use in-memory SQLite for demo
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE vault (
        id INTEGER PRIMARY KEY AUTOINCREMENT, site TEXT, username TEXT,
        password TEXT, notes TEXT DEFAULT '', created_at TEXT, updated_at TEXT)""")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()

    fernet = get_fernet(DEMO_MASTER)
    _set_master_verifier(conn, fernet)

    print_header("Password Manager — Demo Mode")
    print(f"  Master password: {DEMO_MASTER}\n")

    # Add sample entries
    sample = [
        ("GitHub",   "debasish@example.com", "Gh!1secure2024", "Work account"),
        ("Gmail",    "debasish.parida",       "Gm@ilP4ss!",    "Personal email"),
        ("LinkedIn", "debasish_parida",       generate_password(18), ""),
        ("Netflix",  "debasish@example.com",  generate_password(14, use_symbols=False), ""),
    ]
    print("  📥 Adding sample entries...\n")
    for site, user, pw, notes in sample:
        eid = add_entry(conn, fernet, site, user, pw, notes)
        rating, _ = check_strength(pw)
        print(f"  #{eid}  {site:<12} {user:<28} {strength_bar(rating)}")

    print("\n\n  📋 All stored entries:")
    print_row(list_entries(conn))

    print("  🔍 Searching for 'de':")
    print_row(search_entries(conn, "de"))

    print("  🔓 Decrypted entry #1:")
    e = get_entry(conn, fernet, 1)
    print(f"     Site: {e['site']}  User: {e['username']}  Pass: {e['password']}")

    print("\n  🔑 Generated passwords:")
    for length in [12, 16, 20]:
        pw = generate_password(length)
        rating, _ = check_strength(pw)
        print(f"     [{length} chars]  {pw}   {strength_bar(rating)}")
    print()


# ─────────────────────────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "═" * 57)
    print("          🔐  Python Password Manager")
    print("             Secure · Encrypted · Local")
    print("═" * 57)

    conn = init_db()
    fernet = setup_or_login(conn)
    if not fernet:
        conn.close()
        return

    while True:
        print("  ┌─────────────────────────────────┐")
        print("  │  [1] Add entry                  │")
        print("  │  [2] View entry                 │")
        print("  │  [3] List all entries           │")
        print("  │  [4] Search entries             │")
        print("  │  [5] Update password            │")
        print("  │  [6] Delete entry               │")
        print("  │  [7] Generate password          │")
        print("  │  [8] Lock & Exit                │")
        print("  └─────────────────────────────────┘")
        choice = input("\n  Choose (1-8): ").strip()

        actions = {
            "1": lambda: action_add(conn, fernet),
            "2": lambda: action_view(conn, fernet),
            "3": lambda: action_list(conn),
            "4": lambda: action_search(conn),
            "5": lambda: action_update(conn, fernet),
            "6": lambda: action_delete(conn),
            "7": action_generate,
        }

        if choice in actions:
            actions[choice]()
        elif choice == "8":
            conn.close()
            print("\n  🔒 Vault locked. Goodbye!\n")
            break
        else:
            print("  ⚠️  Enter a number from 1 to 8.\n")


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--demo" in sys.argv[1:]:
        run_demo()
    else:
        main()