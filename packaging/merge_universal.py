"""Merge an arm64 and an x86_64 PyInstaller .app into one universal .app.

numpy and matplotlib don't publish universal2 packages, so PyInstaller can't
build a universal app directly. Instead the app is built once per architecture
(with identical package versions) and each pair of Mach-O files is combined
with lipo. Other files must be identical in both builds, or the merge stops.

Usage: python merge_universal.py ARM64.app X86_64.app OUT.app
"""

import filecmp
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

MACHO_MAGIC = {
    b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe",  # thin, little-endian
    b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf",  # fat
}


def is_macho(p: Path) -> bool:
    with open(p, "rb") as f:
        return f.read(4) in MACHO_MAGIC


def archs(p: Path) -> set:
    out = subprocess.run(["lipo", "-archs", str(p)], capture_output=True, text=True, check=True)
    return set(out.stdout.split())


def same_content(a: Path, x: Path) -> bool:
    if filecmp.cmp(a, x, shallow=False):
        return True
    if a.suffix == ".zip":  # zips can differ only in timestamps and file order
        with zipfile.ZipFile(a) as za, zipfile.ZipFile(x) as zx:
            names = sorted(za.namelist())
            return names == sorted(zx.namelist()) and all(za.read(n) == zx.read(n) for n in names)
    return False


def harmless_difference(rel: Path) -> bool:
    # Package metadata records which platform wheel it came from; nothing reads it at run time.
    return rel.name == "Info.plist" or any(p.endswith(".dist-info") for p in rel.parts)


def merge(arm: Path, x86: Path, out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(arm, out, symlinks=True)

    arm_files = {p.relative_to(arm) for p in arm.rglob("*") if p.is_file() and not p.is_symlink()}
    x86_files = {p.relative_to(x86) for p in x86.rglob("*") if p.is_file() and not p.is_symlink()}
    problems = []
    merged = 0

    for rel in sorted(arm_files | x86_files):
        a, x, o = arm / rel, x86 / rel, out / rel
        if "_CodeSignature" in rel.parts:
            continue
        if rel not in arm_files:  # a real file only in the Intel build
            if o.is_symlink():
                continue  # the arm64 build has it as an alias of a file merged below
            if not is_macho(x):
                problems.append(f"only in x86_64 build: {rel}")
                continue
            # A library only the Intel half needs (e.g. libgcc_s); arm64 never loads it.
            o.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(x, o)
            continue
        if not x.exists():
            if not is_macho(a):
                problems.append(f"only in arm64 build: {rel}")
            continue  # a library only the arm64 half needs (e.g. ICU)
        x = x.resolve()  # the Intel build may keep this library under another name
        if is_macho(a) and is_macho(x):
            if archs(a) >= {"arm64", "x86_64"}:  # already universal (e.g. our driver)
                continue
            subprocess.run(["lipo", "-create", str(a), str(x), "-output", str(o)], check=True)
            merged += 1
        elif not same_content(a, x) and not harmless_difference(rel):
            problems.append(f"differs between builds: {rel}")

    if problems:
        print("Merge problems:\n  " + "\n  ".join(problems))
        sys.exit(1)

    shutil.rmtree(out / "Contents" / "_CodeSignature", ignore_errors=True)
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(out)], check=True)
    print(f"Merged {merged} binaries into {out}")


if __name__ == "__main__":
    merge(*(Path(a) for a in sys.argv[1:4]))
