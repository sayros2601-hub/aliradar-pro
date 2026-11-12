#!/usr/bin/env bash
# Tesseract for the daily job (text posters are never used as product photos).
# On 2026-11-11 the runner could not resolve the Ubuntu mirrors and `apt-get install` hung until the
# 25-minute job timeout, so no products were added. apt now gets a hard time limit; if it fails, the
# same program comes from conda-forge (a different network), so one outage never stops the daily drop.
set -uo pipefail

ok() { command -v tesseract >/dev/null 2>&1 && tesseract --list-langs 2>/dev/null | grep -qx eng; }

if [ "${FORCE_OCR_FALLBACK:-0}" != "1" ]; then
  APT="-o Acquire::Retries=2 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 -o DPkg::Lock::Timeout=60"
  timeout 150 sudo apt-get $APT update -y || echo "apt update failed or timed out"
  timeout 240 sudo apt-get $APT install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
    || echo "apt install failed or timed out"
  if ok; then tesseract --version | head -n 1; exit 0; fi
fi

echo "Falling back to conda-forge tesseract"
PREFIX="$HOME/ocr"
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
for attempt in 1 2 3; do
  curl -fsSL --retry 3 --max-time 120 -o "$BIN/micromamba" \
    https://github.com/mamba-org/micromamba-releases/releases/latest/download/micromamba-linux-64 && break
  sleep 10
done
chmod +x "$BIN/micromamba"
for attempt in 1 2 3; do
  timeout 600 "$BIN/micromamba" create -y -q -r "$HOME/.mamba" -p "$PREFIX" -c conda-forge tesseract && break
  sleep 15
done
export PATH="$PREFIX/bin:$PATH"
if [ ! -f "$PREFIX/share/tessdata/eng.traineddata" ]; then
  mkdir -p "$PREFIX/share/tessdata"
  curl -fsSL --retry 3 --max-time 120 -o "$PREFIX/share/tessdata/eng.traineddata" \
    https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata
fi
export TESSDATA_PREFIX="$PREFIX/share/tessdata"
if [ -n "${GITHUB_PATH:-}" ]; then echo "$PREFIX/bin" >> "$GITHUB_PATH"; fi
if [ -n "${GITHUB_ENV:-}" ]; then echo "TESSDATA_PREFIX=$TESSDATA_PREFIX" >> "$GITHUB_ENV"; fi
if ok; then tesseract --version | head -n 1; exit 0; fi
echo "::error::tesseract could not be installed from apt or conda-forge"
exit 1
