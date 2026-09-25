# PyInstaller spec for the macOS app. Build with:  sh packaging/build_mac.sh
from pathlib import Path

ROOT = Path(SPECPATH).parent
DRIVERS = ROOT / "drivers" / "macos"
APP_NAME = "Photoelectric Effect"
VERSION = next(line.split('"')[1] for line in (ROOT / "photoelectric" / "__init__.py").open()
               if line.startswith("__version__"))

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    # Top level of Frameworks, where PyInstaller's @rpath links look for libraries.
    binaries=[(str(p), ".") for p in DRIVERS.glob("*.dylib")],
    hiddenimports=["u6", "LabJackPython"],
    # Optional extras matplotlib/numpy would pull in if installed; the program uses none.
    # sqlite3 alone would add ~40 MB of ICU.
    excludes=["pytest", "IPython", "PyQt5", "PyQt6", "PySide2", "PySide6",
              "scipy", "pandas", "sqlite3"],
)
# PyInstaller also picks up any Exodriver installed in /usr/local/lib on the build
# machine. Drop those copies so the app always uses the ones from drivers/macos.
#
# In a conda environment PyInstaller also bundles every library Python itself
# depends on. SQLite (and ICU, which only SQLite uses) are never loaded: ~40 MB.
a.binaries = [
    b for b in a.binaries
    if (not b[0].startswith(("liblabjackusb", "libusb")) or Path(b[1]).parent == DRIVERS)
    and not b[0].startswith(("libsqlite3", "libicu"))
]
a.datas = [d for d in a.datas if not Path(d[0]).name.startswith(("libsqlite3", "libicu"))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=APP_NAME, console=False)
coll = COLLECT(exe, a.binaries, a.datas, name=APP_NAME)
app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=str(ROOT / "packaging" / "icon.icns"),
    bundle_identifier="io.github.jrmumford.photoelectric-effect",
    version=VERSION,
    info_plist={
        "CFBundleShortVersionString": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
    },
)
