import os
import ctypes
import winreg
import shutil
from datetime import datetime
from pathlib import Path
from src.utils import C, header, info, ok, warn, err, bold, run_cmd, format_size

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

def delete_restore_point():
    header("DELETE RESTORE POINT")
    list_restore_points()
    print()
    choice = input(f"{C.GREEN}  Enter SequenceNumber to delete (or 'all' to delete ALL, Enter to cancel): {C.RESET}").strip().lower()
    
    if not choice:
        info("Cancelled.")
        return
        
    if choice == "all":
        confirm = input(f"{C.RED}  Confirm delete ALL restore points? (y/N): {C.RESET}").strip().lower()
        if confirm == "y":
            run_cmd("vssadmin delete shadows /all /quiet")
            ok("Requested deletion of all shadow copies/restore points.")
        else:
            info("Cancelled.")
        return
        
    if not choice.isdigit():
        err("Invalid input.")
        return
        
    seq = int(choice)
    try:
        srclient = ctypes.WinDLL("srclient.dll")
        res = srclient.SRRemoveRestorePoint(seq)
        if res == 0:
            ok(f"Restore point {seq} deleted successfully.")
        else:
            err(f"Failed to delete restore point {seq}. Error code: {res}")
    except Exception as e:
        err(f"Error calling srclient.dll: {e}")

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

def optimize_services():
    header("WINDOWS SERVICES OPTIMIZER")
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