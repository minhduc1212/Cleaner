import os
import shutil
from pathlib import Path
from hashlib import md5
from src.utils import C, header, info, ok, warn, err, format_size, folder_size

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