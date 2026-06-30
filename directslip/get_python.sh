#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -euo pipefail


SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )


# Default values if parameters are missing
VERSION=${1:-"3.14.6"}
BIN_DIR="$SCRIPT_DIR/bin"
TARGET_DIR="$BIN_DIR/custom_python"
CACHE_DIR="$BIN_DIR/python_sources"
EXTRACT_DIR="$BIN_DIR/python_extract"

# Create necessary directories
mkdir -p "$BIN_DIR"
mkdir -p "$CACHE_DIR"
mkdir -p "$TARGET_DIR"
mkdir -p "$EXTRACT_DIR"

TARBALL="Python-${VERSION}.tgz"
DOWNLOAD_URL="https://www.python.org/ftp/python/${VERSION}/${TARBALL}"
CACHE_PATH="${CACHE_DIR}/${TARBALL}"

echo "========================================================="
echo "Target Python Version : ${VERSION}"
echo "Installation Directory : ${TARGET_DIR}"
echo "Cache Directory        : ${CACHE_DIR}"
echo "========================================================="

# ---- 1. CACHED DOWNLOAD ----
if [ -f "$CACHE_PATH" ]; then
    echo "✓ Found cached source code: ${TARBALL}"
else
    echo "⬇ Downloading Python ${VERSION} from official servers..."
    # -L follows redirects, -C - resumes broken downloads
    curl -L "$DOWNLOAD_URL" -o "$CACHE_PATH"
    echo "✓ Download complete."
fi


# ---- 2. EXTRACT ----
echo "📦 Extracting to temporary directory: ${EXTRACT_DIR}"
tar -xf "$CACHE_PATH" -C "$EXTRACT_DIR"

cd "${EXTRACT_DIR}/Python-${VERSION}"


# CLEAN CACHE DIR
rm -rf "$CACHE_PATH"

# ---- 3. CONFIGURE ----
echo "⚙ Configuring build with maximum optimizations..."
# --prefix controls where the final 'make install' puts the files
./configure \
    --prefix="$TARGET_DIR" \
    --with-lto \
    --enable-optimizations \
    --with-ensurepip=no

# ---- 4. BUILD & INSTALL ----
# Grab the number of available CPU cores (useful if you are on a Pi Zero 2 W)
CORES=$(nproc 2>/dev/null || echo 1)
echo "🛠 Building Python using ${CORES} CPU core(s)..."
echo "⚠️ Note: Profile-Guided Optimization (PGO) takes a long time on low-power hardware."

make -j"$CORES"
echo "💾 Installing to custom directory..."
make altinstall

# ---- 5. CLEANUP TEMPORARY WORK DIR ----
echo "🧹 Cleaning up temporary build files..."
rm -rf "$EXTRACT_DIR"

echo "========================================================="
echo "🎉 Success! Optimized Python installed at:"
echo "👉 ${TARGET_DIR}/bin/python3.${VERSION%.*}"
echo "========================================================="
