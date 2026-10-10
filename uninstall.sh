#!/bin/sh
set -eu
PREFIX=${MOGOJ_INSTALL_DIR:-"$HOME/.local/share/mogoj"}
BIN_DIR=${MOGOJ_BIN_DIR:-"$HOME/.local/bin"}
ASSUME_YES=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --prefix) PREFIX=$2; shift 2 ;;
    --bin-dir) BIN_DIR=$2; shift 2 ;;
    --yes) ASSUME_YES=1; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
echo "This removes the engine at $PREFIX and command at $BIN_DIR/mogoj."
echo "Memory stores are preserved."
if [ "$ASSUME_YES" -ne 1 ] && [ -t 0 ]; then
  printf "Continue? [y/N] "; read answer
  case "$answer" in y|Y|yes|YES) ;; *) echo "Uninstall cancelled."; exit 0 ;; esac
fi
if [ -L "$BIN_DIR/mogoj" ]; then rm -- "$BIN_DIR/mogoj";
elif [ -e "$BIN_DIR/mogoj" ]; then echo "Refusing to remove a command that is not a symlink." >&2; exit 3; fi
if [ -d "$PREFIX" ]; then rm -rf -- "$PREFIX"; fi
echo "Mogoj engine removed. Memory data was not touched."
