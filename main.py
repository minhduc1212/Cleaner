import os
import shutil
import ctypes
import sys
import subprocess
import json
import winreg
from pathlib import Path
from datetime import datetime

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

# ================================================================
# HELPER
# ================================================================
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

# ================================================================
# NEW: CREATE RESTORE POINT
# ================================================================
def create_restore_point():
    header("CREATE SYSTEM RESTORE POINT")
    desc = input(f"{C.GREEN}  Restore Point Name (Enter = 'CleanerBackup_{datetime.now().strftime('%Y%m%d_%H%M')}' ): {C.RESET}").strip()
    if not desc:
        desc = f"CleanerBackup_{datetime.now().strftime('%Y%m%d_%H%M')}"

    info(f"Creating Restore Point: '{desc}' ...")
    ps_cmd = (
        f'powershell -Command "Checkpoint-Computer -Description \'{desc}\' '
        f'-RestorePointType MODIFY_SETTINGS"'
    )
    output = run_cmd(ps_cmd, capture=True)
    if output and "error" in output.lower():
        err(f"Could not create restore point: {output.strip()}")
        warn("Check: Is System Protection enabled?")
        warn("Control Panel > System > System Protection > C: > Configure > Turn on")
    else:
        ok(f"Restore Point '{desc}' created successfully!")
        info("View at: Control Panel > System > System Protection > System Restore")

def list_restore_points():
    header("LIST RESTORE POINTS")
    info("Fetching list...")
    output = run_cmd(
        'powershell -Command "Get-ComputerRestorePoint | '
        'Select-Object SequenceNumber, Description, CreationTime | Format-Table -AutoSize"',
        capture=True
    )
    if output.strip():
        print(f"{C.CYAN}{output}{C.RESET}")
    else:
        warn("No restore points found, or System Protection is disabled.")

# ================================================================
# NEW: STARTUP PROGRAMS MANAGER
# ================================================================
def manage_startup():
    header("STARTUP PROGRAMS MANAGER")
    bold("Windows Startup Programs:")
    print()

    startup_keys = [
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
    ]

    all_entries = []
    for hive, key_path, hive_name in startup_keys:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                i = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, i)
                        all_entries.append((hive_name, key_path, name, val))
                        i += 1
                    except OSError:
                        break
        except Exception:
            pass

    if not all_entries:
        warn("No startup programs found.")
        return

    print(f"  {'#':<4} {'HIVE':<6} {'NAME':<35} {'PATH'}")
    print("  " + "-" * 80)
    for idx, (hive_name, _, name, val) in enumerate(all_entries, 1):
        display_val = val[:55] + "..." if len(val) > 55 else val
        print(f"  {C.YELLOW}{idx:<4}{C.RESET} {C.CYAN}{hive_name:<6}{C.RESET} {name:<35} {display_val}")

    print()
    choice = input(f"{C.GREEN}  Enter number to DELETE from startup (Enter to skip): {C.RESET}").strip()
    if not choice.isdigit():
        info("Skipped, no changes.")
        return

    idx = int(choice) - 1
    if not (0 <= idx < len(all_entries)):
        err("Invalid number.")
        return

    hive_name, key_path, name, val = all_entries[idx]
    hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    confirm = input(f"{C.RED}  Confirm delete '{name}' from startup? (y/N): {C.RESET}").strip().lower()
    if confirm == "y":
        try:
            with winreg.OpenKey(hive, key_path, 0, winreg.KEY_WRITE) as key:
                winreg.DeleteValue(key, name)
            ok(f"Deleted '{name}' from startup.")
        except Exception as e:
            err(f"Could not delete: {e}")
    else:
        info("Cancelled.")

# ================================================================
# NEW: DISK USAGE ANALYZER (per folder on C:\)
# ================================================================
def disk_usage_analyzer():
    header("DISK USAGE ANALYZER C:\\")
    info("Calculating size of main folders (may take a few minutes)...")
    skip = {"$Recycle.Bin", "System Volume Information"}
    results = []
    try:
        for item in Path("C:\\").iterdir():
            if item.name in skip or not item.is_dir():
                continue
            sz = folder_size(item)
            if sz > 0:
                results.append((sz, item))
    except Exception as e:
        err(f"Error: {e}")

    results.sort(reverse=True)
    total = sum(s for s, _ in results)

    print(f"\n  {'SIZE':<14}  {'%':<7}  FOLDER")
    print("  " + "-" * 60)
    for sz, p in results[:20]:
        pct = (sz / total * 100) if total else 0
        bar = "█" * int(pct / 5)
        print(f"  {C.CYAN}{format_size(sz):<14}{C.RESET}  {pct:>5.1f}%  {C.YELLOW}{p}{C.RESET}  {bar}")

    total_disk = shutil.disk_usage("C:\\")
    print(f"\n  Total C:\\ : {format_size(total_disk.total)}")
    print(f"  Used       : {format_size(total_disk.used)}  ({total_disk.used/total_disk.total*100:.1f}%)")
    print(f"  Free       : {C.GREEN}{format_size(total_disk.free)}{C.RESET}")

# ================================================================
# NEW: NETWORK RESET & FLUSH
# ================================================================
def network_reset():
    header("NETWORK RESET & FLUSH")
    warn("This will reset network settings. Continue? (y/N)")
    if input(f"{C.GREEN}  > {C.RESET}").strip().lower() != "y":
        info("Cancelled.")
        return

    steps = [
        ("ipconfig /flushdns",                          "Flush DNS cache"),
        ("netsh int ip reset",                          "Reset IP stack"),
        ("netsh winsock reset",                         "Reset Winsock"),
        ("netsh int tcp reset",                         "Reset TCP"),
        ("arp -d *",                                    "Delete ARP cache"),
        ("nbtstat -R",                                  "Reload NetBIOS"),
    ]
    for cmd, label in steps:
        info(f"{label}...")
        run_cmd(cmd)
        ok(label)

    warn("RESTART required to fully apply changes!")

# ================================================================
# NEW: DUPLICATE FILE FINDER
# ================================================================
def find_duplicates():
    header("FIND DUPLICATE FILES")
    search_path = input(
        f"{C.GREEN}  Enter folder to scan (Enter = Desktop+Downloads): {C.RESET}"
    ).strip()

    if not search_path:
        paths = [
            Path.home() / "Desktop",
            Path.home() / "Downloads",
            Path.home() / "Documents",
        ]
    else:
        paths = [Path(search_path)]

    info("Scanning and calculating file hashes...")
    from hashlib import md5

    size_map = {}
    for base in paths:
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if f.is_file():
                try:
                    sz = f.stat().st_size
                    size_map.setdefault(sz, []).append(f)
                except Exception:
                    pass

    duplicates = []
    for sz, files in size_map.items():
        if len(files) < 2 or sz == 0:
            continue
        hash_map = {}
        for f in files:
            try:
                h = md5(f.read_bytes()).hexdigest()
                hash_map.setdefault(h, []).append(f)
            except Exception:
                pass
        for h, dups in hash_map.items():
            if len(dups) > 1:
                duplicates.append((sz, dups))

    if not duplicates:
        ok("No duplicate files found!")
        return

    duplicates.sort(reverse=True)
    total_wasted = sum(sz * (len(dups) - 1) for sz, dups in duplicates)
    print(f"\n  Found {C.RED}{len(duplicates)}{C.RESET} groups of duplicate files")
    print(f"  Total wasted space: {C.RED}{format_size(total_wasted)}{C.RESET}\n")

    for idx, (sz, dups) in enumerate(duplicates[:10], 1):
        print(f"  {C.YELLOW}[Group {idx}]  {format_size(sz)} each file{C.RESET}")
        for d in dups:
            print(f"     {d}")

    if len(duplicates) > 10:
        print(f"  ... and {len(duplicates)-10} more groups.")

    print()
    choice = input(f"{C.GREEN}  Auto-delete duplicates? Keep 1 original. (y/N): {C.RESET}").strip().lower()
    if choice == "y":
        deleted, freed = 0, 0
        for sz, dups in duplicates:
            for dup in dups[1:]:
                try:
                    dup.unlink()
                    deleted += 1
                    freed += sz
                except Exception:
                    pass
        ok(f"Deleted {deleted} files | Freed {format_size(freed)}")

# ================================================================
# NEW: WINDOWS SERVICES OPTIMIZER
# ================================================================
def optimize_services():
    header("WINDOWS SERVICES OPTIMIZER")
    # Services that are generally safe to disable for performance
    optional_services = [
        ("DiagTrack",         "Connected User Experiences and Telemetry (Telemetry Microsoft)"),
        ("dmwappushservice",  "WAP Push Message Routing Service (Telemetry)"),
        ("WSearch",           "Windows Search (indexing) - disable if fast search not needed"),
        ("SysMain",           "SysMain / Superfetch - can disable on SSD"),
        ("Fax",               "Windows Fax and Scan"),
        ("XblAuthManager",    "Xbox Live Auth Manager"),
        ("XblGameSave",       "Xbox Live Game Save"),
        ("XboxNetApiSvc",     "Xbox Live Networking Service"),
        ("lfsvc",             "Geolocation Service"),
        ("MapsBroker",        "Downloaded Maps Manager"),
    ]

    print(f"\n  {'#':<4} {'SERVICE':<28} DESCRIPTION")
    print("  " + "-" * 80)
    for idx, (svc, desc) in enumerate(optional_services, 1):
        out = run_cmd(f'sc query "{svc}"', capture=True)
        status = "RUNNING" if "RUNNING" in out else ("STOPPED" if "STOPPED" in out else "N/A")
        color = C.RED if status == "RUNNING" else C.GREEN
        print(f"  {C.YELLOW}{idx:<4}{C.RESET} {svc:<28} [{color}{status}{C.RESET}] {desc}")

    print()
    choice = input(
        f"{C.GREEN}  Enter number to DISABLE service (e.g. 1,3,5), 'all' for all, Enter to skip: {C.RESET}"
    ).strip()

    if not choice:
        info("Skipped.")
        return

    if choice.lower() == "all":
        indices = list(range(len(optional_services)))
    else:
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
        except ValueError:
            err("Invalid input.")
            return

    for idx in indices:
        if 0 <= idx < len(optional_services):
            svc, desc = optional_services[idx]
            run_cmd(f'sc config "{svc}" start= disabled')
            run_cmd(f'sc stop "{svc}"')
            ok(f"Disabled: {svc}")

# ================================================================
# NEW: EXPORT REPORT
# ================================================================
def export_report():
    header("EXPORT SYSTEM REPORT")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path.home() / "Desktop" / f"system_report_{ts}.txt"

    lines = []
    lines.append(f"SYSTEM REPORT  -  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    lines.append("=" * 60)

    # Disk usage
    lines.append("\n[DISK USAGE]")
    usage = shutil.disk_usage("C:\\")
    lines.append(f"  Total : {format_size(usage.total)}")
    lines.append(f"  Used  : {format_size(usage.used)}  ({usage.used/usage.total*100:.1f}%)")
    lines.append(f"  Free  : {format_size(usage.free)}")

    # Systeminfo
    lines.append("\n[SYSTEM INFO]")
    out = run_cmd("systeminfo", capture=True)
    for line in out.splitlines()[:25]:
        lines.append(f"  {line}")

    # Running processes top 15 by memory
    lines.append("\n[TOP PROCESSES BY MEMORY]")
    out = run_cmd(
        'powershell -Command "Get-Process | Sort-Object WorkingSet -Descending | '
        'Select-Object -First 15 Name, Id, @{n=\'MB\';e={[math]::Round($_.WorkingSet/1MB,1)}} | '
        'Format-Table -AutoSize"',
        capture=True
    )
    for line in out.splitlines():
        lines.append(f"  {line}")

    # Startup items
    lines.append("\n[STARTUP PROGRAMS]")
    out = run_cmd(
        'powershell -Command "Get-CimInstance Win32_StartupCommand | '
        'Select-Object Name, Command, Location | Format-Table -AutoSize"',
        capture=True
    )
    for line in out.splitlines():
        lines.append(f"  {line}")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    ok(f"Report saved at: {report_path}")

# ================================================================
# 1. TEMP & CACHE HE THONG
# ================================================================
def clean_temp():
    header("1/8  SYSTEM TEMP & CACHE")
    run_cmd("net stop wuauserv")
    run_cmd("net stop bits")
    run_cmd("net stop cryptsvc")
    info("Stopped Windows Update services.")
    targets = [
        (r"C:\Windows\Temp",                          "Windows Temp"),
        (os.environ.get("TEMP", ""),                  "User Temp"),
        (os.environ.get("TMP",  ""),                  "User TMP"),
        (r"C:\Windows\SoftwareDistribution\Download", "Windows Update Cache"),
        (r"C:\Windows\Prefetch",                      "Prefetch"),
        (r"C:\Windows\Logs",                          "Windows Logs"),
        (r"C:\Windows\LiveKernelReports",             "Kernel Crash Dumps"),
        (r"C:\ProgramData\Microsoft\Windows\WER",     "Error Reports (WER)"),
    ]
    for path, label in targets:
        if path:
            clean_folder(path, label)
    run_cmd("net start wuauserv")
    run_cmd("net start bits")
    run_cmd("net start cryptsvc")
    ok("Restarted services.")

# ================================================================
# 2. THUNG RAC
# ================================================================
def clean_recycle_bin():
    header("2/8  RECYCLE BIN")
    run_cmd("rd /s /q C:\\$Recycle.Bin")
    ok("Recycle Bin emptied.")

# ================================================================
# 3. PYTHON / PIP / CONDA
# ================================================================
def clean_python():
    header("3/8  PYTHON / PIP / CONDA")
    la = os.environ.get("LOCALAPPDATA", "")
    up = os.environ.get("USERPROFILE", "")
    targets = [
        (Path(la) / "pip" / "cache",           "pip cache"),
        (Path(la) / "pip" / "http-v2",         "pip HTTP cache"),
        (Path(la) / "virtualenv" / "wheel",    "virtualenv wheel cache"),
        (Path(up) / "anaconda3" / "pkgs",      "Anaconda pkgs"),
        (Path(up) / "miniconda3" / "pkgs",     "Miniconda pkgs"),
    ]
    for path, label in targets:
        clean_folder(path, label)

    info("Deleting __pycache__ in user directory...")
    removed = 0
    try:
        for pc in Path.home().rglob("__pycache__"):
            shutil.rmtree(pc, ignore_errors=True)
            removed += 1
    except Exception:
        pass
    ok(f"Deleted {removed} __pycache__ directories.")

    info("Deleting stray .pyc files...")
    pyc_count = 0
    try:
        for pyc in Path.home().rglob("*.pyc"):
            try:
                pyc.unlink(missing_ok=True)
                pyc_count += 1
            except Exception:
                pass
    except Exception:
        pass
    ok(f"Deleted {pyc_count} .pyc files.")

# ================================================================
# 4. .NET / C# / NUGET / VISUAL STUDIO
# ================================================================
def clean_dotnet():
    header("4/8  .NET / C# / NUGET / VISUAL STUDIO")
    la = os.environ.get("LOCALAPPDATA", "")
    ap = os.environ.get("APPDATA",      "")
    up = os.environ.get("USERPROFILE",  "")
    targets = [
        (Path(up) / ".nuget" / "packages",              "NuGet global packages"),
        (Path(la) / "NuGet"  / "Cache",                 "NuGet HTTP cache"),
        (Path(la) / "Microsoft" / "VisualStudio",       "Visual Studio cache"),
        (Path(ap) / "Microsoft" / "VisualStudio",       "VS AppData cache"),
        (Path(la) / "Microsoft" / "MSBuild",            "MSBuild cache"),
        (Path(la) / "Temp"    / "MSBuildTemp",          "MSBuild Temp"),
        (Path(la) / "Microsoft" / "dotnet",             "dotnet tool cache"),
        (Path(la) / "JetBrains",                        "JetBrains / Rider cache"),
        (Path(la) / "Microsoft" / "CLR_v4.0",          "CLR cache"),
    ]
    for path, label in targets:
        clean_folder(path, label)
    warn("Skipping bin/ and obj/ -- delete manually in projects if needed.")

# ================================================================
# 5. NODE.JS / NPM / YARN / PNPM
# ================================================================
def clean_nodejs():
    header("5/8  NODE.JS / NPM / YARN / PNPM")
    la = os.environ.get("LOCALAPPDATA", "")
    ap = os.environ.get("APPDATA",      "")
    targets = [
        (Path(ap) / "npm-cache",                "npm cache"),
        (Path(la) / "npm-cache",                "npm cache (local)"),
        (Path(la) / "Yarn" / "Data" / "Cache",  "Yarn cache"),
        (Path(la) / "pnpm"  / "store",          "pnpm store"),
    ]
    for path, label in targets:
        clean_folder(path, label)
    ok("Node.js cache cleaned.")

# ================================================================
# 6. CACHE TRINH DUYET
# ================================================================
def clean_browsers():
    header("6/8  BROWSER CACHE")
    la = os.environ.get("LOCALAPPDATA", "")
    ap = os.environ.get("APPDATA",      "")
    ud = "User Data\\Default"
    targets = [
        (Path(la) / "Google"        / "Chrome"        / ud / "Cache",      "Chrome Cache"),
        (Path(la) / "Google"        / "Chrome"        / ud / "Code Cache", "Chrome Code Cache"),
        (Path(la) / "Google"        / "Chrome"        / ud / "GPUCache",   "Chrome GPU Cache"),
        (Path(la) / "Microsoft"     / "Edge"           / ud / "Cache",      "Edge Cache"),
        (Path(la) / "Microsoft"     / "Edge"           / ud / "Code Cache", "Edge Code Cache"),
        (Path(la) / "BraveSoftware" / "Brave-Browser" / ud / "Cache",      "Brave Cache"),
        (Path(ap) / "Opera Software"/ "Opera Stable"  / "Cache",           "Opera Cache"),
        (Path(la) / "Mozilla"       / "Firefox"       / "Profiles",        "Firefox Profiles"),
    ]
    for path, label in targets:
        clean_folder(path, label)

# ================================================================
# 7. OFFICE / TEAMS / ONEDRIVE
# ================================================================
def clean_office():
    header("7/8  OFFICE / TEAMS / ONEDRIVE")
    la = os.environ.get("LOCALAPPDATA", "")
    ap = os.environ.get("APPDATA",      "")
    up = os.environ.get("USERPROFILE",  "")
    teams = Path(la) / "Microsoft" / "Teams"
    targets = [
        (teams / "Cache",                                               "Teams Cache"),
        (teams / "blob_storage",                                        "Teams Blob Storage"),
        (teams / "databases",                                           "Teams Databases"),
        (teams / "GPUCache",                                            "Teams GPU Cache"),
        (teams / "IndexedDB",                                           "Teams IndexedDB"),
        (teams / "Local Storage",                                       "Teams Local Storage"),
        (Path(ap) / "Microsoft" / "Teams",                             "Teams AppData"),
        (Path(la) / "Microsoft" / "Office" / "16.0" / "OfficeFileCache", "Office File Cache"),
        (Path(up) / "AppData" / "Local" / "Microsoft" / "OneDrive" / "logs", "OneDrive Logs"),
    ]
    for path, label in targets:
        clean_folder(path, label)

# ================================================================
# 8. DISM / SFC / DISK CLEANUP
# ================================================================
def clean_advanced():
    header("8/8  DISM / SFC / ADVANCED DISK CLEANUP")
    warn("Running Disk Cleanup (cleanmgr)...")
    run_cmd("cleanmgr /sagerun:1")
    warn("Running DISM (may take 5-10 minutes)...")
    subprocess.run(
        "Dism.exe /online /Cleanup-Image /StartComponentCleanup /ResetBase",
        shell=True
    )
    ok("DISM completed.")
    warn("Running SFC /scannow...")
    subprocess.run("sfc /scannow", shell=True)
    ok("SFC completed.")

# ================================================================
# QUET FILE LON
# ================================================================
def scan_large_files(top_n=15, min_mb=200):
    header(f"SCAN FILES LARGER THAN {min_mb} MB ON C:")
    min_size = min_mb * 1024 * 1024
    skip = {"Windows", "ProgramData", "$Recycle.Bin", "System Volume Information"}
    large = []
    print("  (Scanning -- press Ctrl+C to stop early)")
    try:
        for root, dirs, files in os.walk("C:\\"):
            dirs[:] = [d for d in dirs if d not in skip]
            for name in files:
                try:
                    fp = os.path.join(root, name)
                    sz = os.path.getsize(fp)
                    if sz >= min_size:
                        large.append((sz, fp))
                except Exception:
                    pass
    except KeyboardInterrupt:
        warn("Scan cancelled early.")

    large.sort(reverse=True)
    print(f"\n  {'SIZE':<14}  PATH")
    print("  " + "-" * 70)
    for sz, fp in large[:top_n]:
        print(f"  {format_size(sz):<14}  {fp}")
    if not large:
        ok(f"No files larger than {min_mb} MB found.")

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
        choice = input(f"{C.GREEN}  Select [0-9 / R/L/D/F/S/V/N/E]: {C.RESET}").strip().lower()

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