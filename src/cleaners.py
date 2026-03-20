import os
import shutil
import subprocess
from pathlib import Path
from src.utils import header, info, ok, warn, run_cmd, clean_folder

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

def clean_recycle_bin():
    header("2/8  RECYCLE BIN")
    run_cmd("rd /s /q C:\\$Recycle.Bin")
    ok("Recycle Bin emptied.")

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