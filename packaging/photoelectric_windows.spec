# PyInstaller spec for Windows. GitHub Actions runs this (see .github/workflows/build.yml).
# Locally, on Windows:  pyinstaller packaging/photoelectric_windows.spec
#
# The LabJack UD driver is not bundled: it includes a USB kernel driver, so
# LabJack's own installer must be run once on each PC.
from pathlib import Path

ROOT = Path(SPECPATH).parent
APP_NAME = "Photoelectric Effect"

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    hiddenimports=["u6", "LabJackPython"],
    excludes=["pytest", "IPython", "PyQt5", "PyQt6", "PySide2", "PySide6",
              "scipy", "pandas", "sqlite3"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=APP_NAME,
    icon=str(ROOT / "packaging" / "icon.ico"),
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name=APP_NAME)
