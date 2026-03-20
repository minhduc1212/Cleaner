import os
import sys
import ctypes
import subprocess
import shutil
from pathlib import Path

# ================================================================
# ENABLE ANSI COLOR + UTF-8 ON WINDOWS CMD / POWERSHELL
# ================================================================
def enable_windows_ansi():
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

enable_windows_ansi()

# ================================================================
# COLORS
# ================================================================
class C:
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"

def header(msg):
    bar = "=" * 54
    print(f"\n{C.BOLD}{C.CYAN}{bar}\n  {msg}\n{bar}{C.RESET}")

def info(msg):  print(f"{C.BLUE}  >> {msg}{C.RESET}")
def ok(msg):    print(f"{C.GREEN}  [OK] {msg}{C.RESET}")
def warn(msg):  print(f"{C.YELLOW}  [!]  {msg}{C.RESET}")
def err(msg):   print(f"{C.RED}  [X]  {msg}{C.RESET}")
def bold(msg):  print(f"{C.BOLD}{C.MAGENTA}  {msg}{C.RESET}")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_cmd(cmd, capture=False):
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout + result.stderr
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        err(f"Command error: {e}")
        return ""

def format_size(b):
    if b >= 1 << 30: return f"{b/(1<<30):.2f} GB"
    if b >= 1 << 20: return f"{b/(1<<20):.1f} MB"
    if b >= 1 << 10: return f"{b/(1<<10):.1f} KB"
    return f"{b} B"

def folder_size(p: Path):
    try:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    except Exception:
        return 0

def clean_folder(path, label=""):
    p = Path(path)
    label = label or str(path)
    if not p.exists():
        return 0, 0
    info(f"Cleaning: {label}")
    count, freed = 0, 0
    for item in p.glob("*"):
        try:
            if item.is_file() or item.is_symlink():
                freed += item.stat().st_size
                item.unlink(missing_ok=True)
                count += 1
            elif item.is_dir():
                freed += folder_size(item)
                shutil.rmtree(item, ignore_errors=True)
                count += 1
        except PermissionError:
            pass
        except Exception:
            pass
    ok(f"Deleted {count} items  |  Freed ~{format_size(freed)}")
    return count, freed