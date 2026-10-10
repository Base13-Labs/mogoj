#!/bin/sh
set -eu

PREFIX=${MOGOJ_INSTALL_DIR:-"$HOME/.local/share/mogoj"}
BIN_DIR=${MOGOJ_BIN_DIR:-"$HOME/.local/bin"}
SOURCE=""
ASSUME_YES=0
ONBOARD=1
REPOSITORY_URL="https://github.com/Base13-Labs/mogoj"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --prefix) PREFIX=$2; shift 2 ;;
    --bin-dir) BIN_DIR=$2; shift 2 ;;
    --source) SOURCE=$2; shift 2 ;;
    --yes) ASSUME_YES=1; shift ;;
    --no-onboard) ONBOARD=0; shift ;;
    --help) echo "Usage: install.sh [--yes] [--no-onboard] [--prefix DIR] [--bin-dir DIR]"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || true)
if [ -z "$SOURCE" ] && [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/VERSION" ]; then SOURCE=$SCRIPT_DIR; fi

TEMP_DIR=""
cleanup() { if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then rm -rf -- "$TEMP_DIR"; fi; }
trap cleanup EXIT HUP INT TERM

if [ -z "$SOURCE" ]; then
  command -v curl >/dev/null 2>&1 || { echo "Mogoj needs curl. Install curl, then retry." >&2; exit 4; }
  TEMP_DIR=$(mktemp -d)
  echo "Downloading Mogoj from $REPOSITORY_URL over HTTPS..."
  curl -fsSL "$REPOSITORY_URL/archive/refs/heads/main.tar.gz" -o "$TEMP_DIR/mogoj.tar.gz" || {
    echo "Download failed. Check your connection, then retry the same command." >&2; exit 4;
  }
  tar -xzf "$TEMP_DIR/mogoj.tar.gz" -C "$TEMP_DIR"
  SOURCE=$(find "$TEMP_DIR" -mindepth 1 -maxdepth 1 -type d -name 'mogoj-*' | head -n 1)
fi

if [ ! -f "$SOURCE/VERSION" ] || [ ! -f "$SOURCE/bin/mogoj" ]; then
  echo "The package is incomplete; VERSION or bin/mogoj is missing." >&2; exit 3
fi

VERSION=$(sed -n '1p' "$SOURCE/VERSION")
DESTINATION="$PREFIX/$VERSION"
echo "Mogoj $VERSION will create:"
echo "  Engine:  $DESTINATION"
echo "  Command: $BIN_DIR/mogoj"
echo "Memory is separate and survives upgrades and uninstall."
if [ "$ASSUME_YES" -ne 1 ] && [ -t 0 ]; then
  printf "Continue? [Y/n] "; read answer
  case "$answer" in n|N|no|NO) echo "Installation cancelled."; exit 0 ;; esac
fi

mkdir -p "$PREFIX" "$BIN_DIR"
if [ ! -d "$DESTINATION" ]; then
  STAGING="$PREFIX/.install-$VERSION-$$"
  cp -R "$SOURCE" "$STAGING"
  mv "$STAGING" "$DESTINATION"
fi
ln -sfn "$DESTINATION/bin/mogoj" "$BIN_DIR/mogoj"
chmod +x "$DESTINATION/bin/mogoj" "$DESTINATION/tools/cli.py"

echo "Installed successfully."
case ":$PATH:" in
  *":$BIN_DIR:"*) COMMAND=mogoj ;;
  *) COMMAND="$BIN_DIR/mogoj"; echo "Use the full command below; no shell-profile edit is required." ;;
esac
if [ "$ONBOARD" -eq 1 ] && [ -t 0 ]; then "$BIN_DIR/mogoj" onboard; else echo "Start here: $COMMAND onboard"; fi
