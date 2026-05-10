"""
Clipboard Guard Pro - Caret Position Tracking Version
Tracks actual text input focus position for precise switching
"""

import os
import sys
import time
import json
import zlib
import base64
import shutil
import sqlite3
import hashlib
import re
from datetime import datetime, timedelta
import ctypes
from ctypes import wintypes

import pyperclip
from PIL import ImageGrab
from cryptography.fernet import Fernet
import win32gui
import win32process
import psutil


# ==========================================================
# CONFIG
# ==========================================================

DB_NAME = "clipboard_live.db"
ARCHIVE_DIR = "archive"
BACKUP_DIR = "backups"
KEY_FILE = "secret.key"

POLL_INTERVAL = 0.05  # Check 20 times per second
RETENTION_DAYS = 30
MAX_BACKUPS = 3


# ==========================================================
# WINDOWS API FOR CARET TRACKING
# ==========================================================

# Load user32.dll
user32 = ctypes.windll.user32

# Define structures
class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('hwndActive', wintypes.HWND),
        ('hwndFocus', wintypes.HWND),
        ('hwndCapture', wintypes.HWND),
        ('hwndMenuOwner', wintypes.HWND),
        ('hwndMoveSize', wintypes.HWND),
        ('hwndCaret', wintypes.HWND),
        ('rcCaret', wintypes.RECT),
    ]


def get_focused_window_process():
    """
    Get the process name of the window that has KEYBOARD FOCUS (caret)
    This is more accurate than GetForegroundWindow
    """
    try:
        # Get GUI thread info for current thread
        gui_info = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
        
        # Get the foreground thread
        foreground_hwnd = user32.GetForegroundWindow()
        foreground_thread_id = user32.GetWindowThreadProcessId(foreground_hwnd, None)
        
        # Get thread info
        if user32.GetGUIThreadInfo(foreground_thread_id, ctypes.byref(gui_info)):
            # Get the window with actual keyboard focus
            focused_hwnd = gui_info.hwndFocus
            
            # If no focus window, use active window
            if not focused_hwnd:
                focused_hwnd = gui_info.hwndActive
            
            # If still nothing, use foreground window
            if not focused_hwnd:
                focused_hwnd = foreground_hwnd
            
            # Get process from focused window
            if focused_hwnd:
                _, pid = win32process.GetWindowThreadProcessId(focused_hwnd)
                process = psutil.Process(pid)
                return process.name().lower(), focused_hwnd
        
        # Fallback to foreground window
        _, pid = win32process.GetWindowThreadProcessId(foreground_hwnd)
        process = psutil.Process(pid)
        return process.name().lower(), foreground_hwnd
        
    except Exception as e:
        return None, None


def get_caret_position():
    """
    Get actual caret (text cursor) position
    Returns (hwnd, x, y) or (None, None, None)
    """
    try:
        gui_info = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
        foreground_hwnd = user32.GetForegroundWindow()
        foreground_thread_id = user32.GetWindowThreadProcessId(foreground_hwnd, None)
        
        if user32.GetGUIThreadInfo(foreground_thread_id, ctypes.byref(gui_info)):
            caret_hwnd = gui_info.hwndCaret
            if caret_hwnd:
                rect = gui_info.rcCaret
                return caret_hwnd, rect.left, rect.top
        
        return None, None, None
    except:
        return None, None, None


# ==========================================================
# SECURITY LAYER
# ==========================================================

def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


def load_key():
    if not os.path.exists(KEY_FILE):
        return generate_key()
    return open(KEY_FILE, "rb").read()


fernet = Fernet(load_key())


def encrypt_compress(data: bytes) -> bytes:
    return fernet.encrypt(zlib.compress(data))


def decrypt_decompress(data: bytes) -> bytes:
    return zlib.decompress(fernet.decrypt(data))


# ==========================================================
# DIRECTORY SETUP
# ==========================================================

def ensure_dirs():
    for d in [ARCHIVE_DIR, BACKUP_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)


ensure_dirs()


# ==========================================================
# DATABASE SETUP
# ==========================================================

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS clipboard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    content BLOB,
    timestamp TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT,
    replacement TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS target_apps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process_name TEXT UNIQUE
)
""")

conn.commit()


# ==========================================================
# BACKUP ENGINE
# ==========================================================

def rotate_backups():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")
    shutil.copy2(DB_NAME, backup_file)

    backups = sorted(os.listdir(BACKUP_DIR))
    while len(backups) > MAX_BACKUPS:
        os.remove(os.path.join(BACKUP_DIR, backups[0]))
        backups.pop(0)


# ==========================================================
# SETTINGS ENGINE
# ==========================================================

def initialize_settings():
    defaults = {
        "save_text": "1",
        "save_images": "1"
    }

    for k, v in defaults.items():
        cursor.execute(
            "INSERT OR IGNORE INTO settings (key,value) VALUES (?,?)",
            (k, v)
        )
    conn.commit()


initialize_settings()


def get_setting(key):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    r = cursor.fetchone()
    return r and r[0] == "1"


def set_setting(key, enabled):
    rotate_backups()
    cursor.execute(
        "UPDATE settings SET value=? WHERE key=?",
        ("1" if enabled else "0", key)
    )
    conn.commit()


# ==========================================================
# KEYWORD ENGINE
# ==========================================================

def get_keywords():
    cursor.execute("SELECT id, keyword, replacement FROM keywords")
    return cursor.fetchall()


def add_keyword(keyword, replacement):
    rotate_backups()
    cursor.execute(
        "INSERT INTO keywords (keyword,replacement) VALUES (?,?)",
        (keyword, replacement)
    )
    conn.commit()


def update_keyword(keyword_id, new_k, new_r):
    rotate_backups()
    cursor.execute(
        "UPDATE keywords SET keyword=?,replacement=? WHERE id=?",
        (new_k, new_r, keyword_id)
    )
    conn.commit()


def delete_keyword(keyword_id):
    rotate_backups()
    cursor.execute("DELETE FROM keywords WHERE id=?", (keyword_id,))
    conn.commit()


def apply_replacements(text):
    for _, k, r in get_keywords():
        text = re.sub(re.escape(k), r, text, flags=re.IGNORECASE)
    return text


# ==========================================================
# TARGET APP ENGINE
# ==========================================================

def add_target_app(name):
    rotate_backups()
    cursor.execute(
        "INSERT OR IGNORE INTO target_apps (process_name) VALUES (?)",
        (name.lower(),)
    )
    conn.commit()


def remove_target_app(name):
    rotate_backups()
    cursor.execute(
        "DELETE FROM target_apps WHERE process_name=?",
        (name.lower(),)
    )
    conn.commit()


def get_target_apps():
    cursor.execute("SELECT process_name FROM target_apps")
    return [row[0] for row in cursor.fetchall()]


# ==========================================================
# STORAGE ENGINE
# ==========================================================

def save_text(text):
    if not get_setting("save_text"):
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    encrypted = encrypt_compress(text.encode())

    cursor.execute(
        "INSERT INTO clipboard (type,content,timestamp) VALUES (?,?,?)",
        ("text", encrypted, ts)
    )
    conn.commit()


def save_image(img):
    if not get_setting("save_images"):
        return

    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    encrypted = encrypt_compress(buffer.getvalue())

    cursor.execute(
        "INSERT INTO clipboard (type,content,timestamp) VALUES (?,?,?)",
        ("image", encrypted, ts)
    )
    conn.commit()


# ==========================================================
# ARCHIVE ENGINE
# ==========================================================

def archive_old_entries():
    cutoff = datetime.now().date() - timedelta(days=RETENTION_DAYS)

    cursor.execute("SELECT DISTINCT date(timestamp) FROM clipboard")
    dates = cursor.fetchall()

    for (d,) in dates:
        entry_date = datetime.strptime(d, "%Y-%m-%d").date()

        if entry_date < cutoff:
            archive_file = os.path.join(ARCHIVE_DIR, f"{d}.arc")
            if os.path.exists(archive_file):
                continue

            cursor.execute(
                "SELECT type,content,timestamp FROM clipboard WHERE date(timestamp)=?",
                (d,)
            )
            rows = cursor.fetchall()

            archive_data = []
            for t, content, ts in rows:
                archive_data.append({
                    "type": t,
                    "content": base64.b64encode(content).decode(),
                    "timestamp": ts
                })

            encrypted = encrypt_compress(json.dumps(archive_data).encode())

            with open(archive_file, "wb") as f:
                f.write(encrypted)

            cursor.execute(
                "DELETE FROM clipboard WHERE date(timestamp)=?",
                (d,)
            )
            conn.commit()


# ==========================================================
# CLIPBOARD INTELLIGENCE ENGINE - CARET TRACKING
# ==========================================================

# Global state
last_clip_hash = ""
original_text = None
replaced_text = None
last_focused_process = None
last_focused_hwnd = None
current_clipboard_version = None  # What's currently in clipboard


def handle_new_copy(text):
    """Called when user copies new text"""
    global original_text, replaced_text, current_clipboard_version
    
    original_text = text
    replaced_text = apply_replacements(text)
    current_clipboard_version = None  # Force re-evaluation
    
    save_text(text)
    
    has_replacements = (original_text != replaced_text)
    print(f"\n[NEW COPY] {len(text)} chars | Replacements: {has_replacements}")
    if has_replacements:
        print(f"  Original: {original_text[:50]}...")
        print(f"  Replaced: {replaced_text[:50]}...")


def track_caret_and_switch_clipboard():
    """
    CRITICAL: Track where the caret (text cursor) is
    Switch clipboard based on caret location, not just active window
    """
    global last_focused_process, last_focused_hwnd, current_clipboard_version
    
    # Must have cached text
    if not original_text or not replaced_text:
        return
    
    # Get the window with actual keyboard focus (where caret is)
    focused_process, focused_hwnd = get_focused_window_process()
    
    if not focused_process:
        return
    
    # Detect focus change
    focus_changed = (
        focused_process != last_focused_process or 
        focused_hwnd != last_focused_hwnd
    )
    
    if focus_changed:
        last_focused_process = focused_process
        last_focused_hwnd = focused_hwnd
        
        # Also try to get actual caret position
        caret_hwnd, caret_x, caret_y = get_caret_position()
        if caret_hwnd:
            print(f"\n[FOCUS CHANGE] → {focused_process} (caret at {caret_x},{caret_y})")
        else:
            print(f"\n[FOCUS CHANGE] → {focused_process}")
    
    # Get target apps
    target_apps = get_target_apps()
    
    # Determine correct version based on WHERE CARET IS
    is_target = focused_process in target_apps
    correct_version = "replaced" if is_target else "original"
    
    # Switch ONLY if current clipboard doesn't match correct version
    if current_clipboard_version != correct_version:
        try:
            if is_target:
                # Caret is in target app - use REPLACED
                pyperclip.copy(replaced_text)
                current_clipboard_version = "replaced"
                print(f"[CLIPBOARD] ✓ REPLACED → Ready for paste in {focused_process}")
            else:
                # Caret is in non-target app - use ORIGINAL
                pyperclip.copy(original_text)
                current_clipboard_version = "original"
                print(f"[CLIPBOARD] ○ ORIGINAL → Ready for paste in {focused_process}")
        except Exception as e:
            print(f"[ERROR] Clipboard switch failed: {e}")


# ==========================================================
# MONITOR ENGINE - CARET TRACKING
# ==========================================================

def monitor_clipboard():
    global last_clip_hash
    
    print("="*70)
    print("Clipboard Guard Pro - CARET POSITION TRACKING")
    print("="*70)
    print("Tracking: Keyboard focus + Caret position")
    print(f"Text Saving: {get_setting('save_text')}")
    print(f"Image Saving: {get_setting('save_images')}")
    print(f"Target Apps: {get_target_apps()}")
    print(f"Polling Rate: {int(1/POLL_INTERVAL)} checks/second")
    print("="*70)
    print("\nMonitoring started. Switch windows to see tracking...\n")

    archive_old_entries()
    
    iteration = 0

    while True:
        try:
            iteration += 1
            
            # PRIORITY 1: ALWAYS track caret and ensure correct clipboard
            track_caret_and_switch_clipboard()
            
            # PRIORITY 2: Check for new clipboard content (every 4th cycle)
            if iteration % 4 == 0:
                try:
                    current_clip = pyperclip.paste()
                    
                    if isinstance(current_clip, str) and current_clip.strip():
                        clip_hash = hashlib.sha256(current_clip.encode()).hexdigest()
                        
                        # New content detected
                        if clip_hash != last_clip_hash:
                            # Make sure it's not our own cached versions
                            is_our_original = (current_clip == original_text)
                            is_our_replaced = (current_clip == replaced_text)
                            
                            if not is_our_original and not is_our_replaced:
                                # Genuinely new content from user
                                last_clip_hash = clip_hash
                                handle_new_copy(current_clip)
                except Exception as e:
                    pass
            
            # PRIORITY 3: Check for images (every 20th cycle)
            if iteration % 20 == 0:
                try:
                    img = ImageGrab.grabclipboard()
                    if img:
                        save_image(img)
                        print("[IMAGE] Saved to database")
                except:
                    pass

        except Exception as e:
            print(f"[ERROR] Monitor: {e}")

        time.sleep(POLL_INTERVAL)


# ==========================================================
# GUI SUPPORT FUNCTIONS
# ==========================================================

def get_live_entries():
    cursor.execute("SELECT id,type,content,timestamp FROM clipboard ORDER BY timestamp DESC")
    return cursor.fetchall()


def delete_live_entry(entry_id):
    rotate_backups()
    cursor.execute("DELETE FROM clipboard WHERE id=?", (entry_id,))
    conn.commit()


def read_archive_file(file_path):
    with open(file_path, "rb") as f:
        encrypted = f.read()
    data = decrypt_decompress(encrypted)
    return json.loads(data.decode())


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    exe_name = os.path.basename(sys.argv[0]).lower()

    if "monitor" in exe_name:
        monitor_clipboard()

    else:
        while True:
            print("\n" + "="*50)
            print("Clipboard Guard Pro - Caret Tracking Edition")
            print("="*50)
            print("1. Start Monitoring")
            print("2. Toggle Text Saving")
            print("3. Toggle Image Saving")
            print("4. Add Keyword")
            print("5. Show Keywords")
            print("6. Delete Keyword")
            print("7. Add Target App")
            print("8. Show Target Apps")
            print("9. Remove Target App")
            print("10. Test Current Focus")
            print("11. Exit")
            print("="*50)

            c = input("Choose option: ").strip()

            if c == "1":
                monitor_clipboard()
            
            elif c == "2":
                current = get_setting("save_text")
                set_setting("save_text", not current)
                status = "ENABLED" if not current else "DISABLED"
                print(f"✓ Text Saving: {status}")
            
            elif c == "3":
                current = get_setting("save_images")
                set_setting("save_images", not current)
                status = "ENABLED" if not current else "DISABLED"
                print(f"✓ Image Saving: {status}")
            
            elif c == "4":
                k = input("Keyword: ").strip()
                r = input("Replacement: ").strip()
                if k and r:
                    add_keyword(k, r)
                    print(f"✓ Added: '{k}' → '{r}'")
            
            elif c == "5":
                keywords = get_keywords()
                if keywords:
                    print("\n--- Keywords ---")
                    for id, kw, rep in keywords:
                        print(f"  [{id}] '{kw}' → '{rep}'")
                else:
                    print("No keywords")
            
            elif c == "6":
                keywords = get_keywords()
                if keywords:
                    print("\n--- Keywords ---")
                    for id, kw, rep in keywords:
                        print(f"  [{id}] '{kw}' → '{rep}'")
                    kid = input("Enter ID to delete: ").strip()
                    try:
                        delete_keyword(int(kid))
                        print("✓ Deleted")
                    except:
                        print("✗ Invalid ID")
            
            elif c == "7":
                p = input("Process name (e.g. chrome.exe): ").strip()
                if p:
                    add_target_app(p)
                    print(f"✓ Added: {p}")
            
            elif c == "8":
                apps = get_target_apps()
                if apps:
                    print("\n--- Target Apps ---")
                    for app in apps:
                        print(f"  • {app}")
                else:
                    print("No target apps configured")
            
            elif c == "9":
                apps = get_target_apps()
                if apps:
                    print("\n--- Target Apps ---")
                    for i, app in enumerate(apps, 1):
                        print(f"  {i}. {app}")
                    choice = input("Number to remove: ").strip()
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(apps):
                            remove_target_app(apps[idx])
                            print(f"✓ Removed")
                    except:
                        print("✗ Invalid")
            
            elif c == "10":
                # Test current focus detection
                print("\nClick in any text field and press Enter...")
                input()
                
                proc, hwnd = get_focused_window_process()
                caret_hwnd, x, y = get_caret_position()
                
                print(f"\nFocused Process: {proc}")
                print(f"Focused HWND: {hwnd}")
                print(f"Caret HWND: {caret_hwnd}")
                print(f"Caret Position: ({x}, {y})")
                
                target_apps = get_target_apps()
                is_target = proc in target_apps if proc else False
                print(f"Is Target App: {is_target}")
            
            elif c == "11":
                print("\n👋 Goodbye!\n")
                break
