#!/bin/sh
# Builds a universal (Intel + Apple Silicon) "Photoelectric Effect.app" and .dmg.
# Output goes to dist/. Run on an Apple Silicon Mac with Rosetta and conda installed:
#     sh packaging/build_mac.sh
#
# numpy and matplotlib have no universal2 packages, so the app is built twice
# from identical, pinned conda-forge environments (one per architecture) and
# the two builds are merged with lipo by merge_universal.py.
set -e
cd "$(dirname "$0")/.."

PACKAGES="python=3.12.14 numpy=2.5.3 matplotlib-base=3.11.2 pillow=12.3.0 tk=8.6.13 \
contourpy=1.4.0 kiwisolver=1.5.1 fonttools=4.66.0 pyinstaller=6.22.3 pip"
LABJACKPYTHON="LabJackPython==2.3.0"

command -v conda >/dev/null || { echo "conda is required (miniconda or miniforge)."; exit 1; }
arch -x86_64 /usr/bin/true 2>/dev/null || {
    echo "Rosetta is required:  sudo softwareupdate --install-rosetta --agree-to-license"; exit 1; }

build_half() {  # $1 = arm64 | x86_64
    env="build/env-$1"
    subdir=$([ "$1" = arm64 ] && echo osx-arm64 || echo osx-64)
    if [ ! -x "$env/bin/python" ]; then
        echo "Creating $1 build environment..."
        CONDA_SUBDIR=$subdir conda create -q -y -p "$env" -c conda-forge --override-channels $PACKAGES
        arch -$1 "$env/bin/python" -m pip -q install --no-deps "$LABJACKPYTHON"
    fi
    echo "Building $1 app..."
    arch -$1 "$env/bin/python" -m PyInstaller --noconfirm --clean --log-level WARN \
        --distpath "build/$1" --workpath "build/work-$1" packaging/photoelectric_mac.spec
}

build_half arm64
build_half x86_64

APP="dist/Photoelectric Effect.app"
mkdir -p dist
build/env-arm64/bin/python packaging/merge_universal.py \
    "build/arm64/Photoelectric Effect.app" "build/x86_64/Photoelectric Effect.app" "$APP"

DMG="dist/Photoelectric Effect.dmg"
STAGE="build/dmg"
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -quiet -volname "Photoelectric Effect" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
echo "Built: $APP"
echo "       $DMG"
