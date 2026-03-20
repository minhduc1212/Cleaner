import sys
import ctypes
from datetime import datetime

from src.utils import C, warn, is_admin
from src.cleaners import (
    clean_temp, clean_recycle_bin, clean_python, clean_dotnet,
    clean_nodejs, clean_browsers, clean_office, clean_advanced
)
from src.system import (
    create_restore_point, list_restore_points, delete_restore_point,
    manage_startup, optimize_services, network_reset, export_report
)
from src.disk import disk_usage_analyzer, find_duplicates, scan_large_files

# ================================================================
# MENU
# ================================================================
MENU = [
    ("",   f"{C.BOLD}--- CLEANUP ---{C.RESET}"),
    ("1",  "Clean ALL (Run everything)"),
    ("2",  "System Temp & Cache"),
    ("3",  "Python / pip / Conda"),
    ("4",  ".NET / C# / NuGet / Visual Studio"),
    ("5",  "Node.js / npm / Yarn / pnpm"),
    ("6",  "Browsers (Chrome, Edge, Firefox...)"),
    ("7",  "Office / Teams / OneDrive"),
    ("8",  "DISM / SFC / Advanced Disk Cleanup"),
    ("9",  "Scan large files (> 200 MB)"),
    ("",   f"{C.BOLD}--- RECOVERY & SAFETY ---{C.RESET}"),
    ("R",  "Create System Restore Point  [NEW]"),
    ("L",  "List Restore Points          [NEW]"),
    ("X",  "Delete Restore Point         [NEW]"),
    ("",   f"{C.BOLD}--- ANALYZE & OPTIMIZE ---{C.RESET}"),
    ("D",  "Disk Usage Analyzer          [NEW]"),
    ("F",  "Find Duplicate Files         [NEW]"),
    ("S",  "Manage Startup Programs      [NEW]"),
    ("V",  "Optimize Windows Services    [NEW]"),
    ("N",  "Reset / Flush Network        [NEW]"),
    ("E",  "Export System Report (TXT)   [NEW]"),
    ("",   ""),
    ("0",  "Exit"),
]

ACTIONS = {
    "1": lambda: [clean_temp(), clean_recycle_bin(), clean_python(),
                  clean_dotnet(), clean_nodejs(), clean_browsers(),
                  clean_office(), clean_advanced(), scan_large_files()],
    "2": clean_temp,
    "3": clean_python,
    "4": clean_dotnet,
    "5": clean_nodejs,
    "6": clean_browsers,
    "7": clean_office,
    "8": clean_advanced,
    "9": scan_large_files,
    "r": create_restore_point,
    "l": list_restore_points,
    "x": delete_restore_point,
    "d": disk_usage_analyzer,
    "f": find_duplicates,
    "s": manage_startup,
    "v": optimize_services,
    "n": network_reset,
    "e": export_report,
}

def print_menu():
    bar = "=" * 54
    print(f"\n{C.BOLD}{C.CYAN}{bar}")
    print(f"      DISK CLEANER  --  WINDOWS OPTIMIZER v2")
    print(f"{bar}{C.RESET}\n")
    for key, label in MENU:
        if key == "":
            print(f"  {label}")
            continue
        if key == "0":
            print(f"  {C.RED}[{key}]{C.RESET}  {label}")
        elif key.isdigit():
            print(f"  {C.YELLOW}[{key}]{C.RESET}  {label}")
        else:
            print(f"  {C.MAGENTA}[{key}]{C.RESET}  {label}")
    print()

# ================================================================
# MAIN
# ================================================================
def main():
    if not is_admin():
        warn("Administrator rights required -- requesting...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            " ".join(f'"{a}"' for a in sys.argv),
            None, 1
        )
        sys.exit(0)

    start = datetime.now()

    while True:
        print_menu()
        choice = input(f"{C.GREEN}  Select [0-9 / R/L/X/D/F/S/V/N/E]: {C.RESET}").strip().lower()

        if choice == "0":
            print(f"\n{C.CYAN}  Goodbye!{C.RESET}\n")
            break

        action = ACTIONS.get(choice)
        if action:
            action()
            elapsed = int((datetime.now() - start).total_seconds())
            print(f"\n{C.GREEN}  [DONE] Elapsed time: {elapsed}s{C.RESET}")
        else:
            warn("Invalid selection, please try again.")

        input(f"\n  {C.YELLOW}Press Enter to return to menu...{C.RESET}")

if __name__ == "__main__":
    main()