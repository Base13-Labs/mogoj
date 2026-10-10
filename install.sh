#!/bin/bash
# Legacy Mogoj installer. The packaged CLI is the preferred installation path.

set -e

MOGOJ_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$HOME/.claude/commands"
DEFAULT_ROOT="$HOME/code/brain"
WITH_ADDONS=0

if [ "${1:-}" = "--with-addons" ]; then
  WITH_ADDONS=1
  shift
fi

mkdir -p "$TARGET_DIR"

echo "Mogoj (মগজ) — installing memory system"
echo ""

# Install skills
count=0
for skill in "$MOGOJ_DIR"/skills/*.md; do
  [ -f "$skill" ] || continue
  name=$(basename "$skill")
  ln -sf "$skill" "$TARGET_DIR/$name"
  echo "  + $name"
  ((count++))
done

if [ "$WITH_ADDONS" -eq 1 ]; then
  for skill in "$MOGOJ_DIR"/addons/workflows/skills/*.md; do
    [ -f "$skill" ] || continue
    name=$(basename "$skill")
    ln -sf "$skill" "$TARGET_DIR/$name"
    echo "  + $name (optional add-on)"
    ((count++))
  done
fi

echo ""
echo "$count skills installed to $TARGET_DIR"

# Set up MOGOJ_ROOT if not already set
if [ -z "$MOGOJ_ROOT" ]; then
  echo ""
  echo "MOGOJ_ROOT not set. Add to your shell profile:"
  echo ""
  echo "  export MOGOJ_ROOT=$DEFAULT_ROOT"
  echo "  export MOGOJ_TOOLS=$MOGOJ_DIR/tools"
  echo ""
fi

# Initialize memory store if it doesn't exist
if [ -n "${1:-}" ]; then
  STORE_DIR="$1"
elif [ -n "$MOGOJ_ROOT" ]; then
  STORE_DIR="$MOGOJ_ROOT"
else
  STORE_DIR="$DEFAULT_ROOT"
fi

if [ ! -d "$STORE_DIR/data" ]; then
  echo "Initializing memory store at $STORE_DIR..."
  cp -r "$MOGOJ_DIR/template/"* "$STORE_DIR/" 2>/dev/null || true
  mkdir -p "$STORE_DIR/data/index" "$STORE_DIR/data/ram/archive" "$STORE_DIR/data/sessions"
  mkdir -p "$STORE_DIR/docs/company" "$STORE_DIR/docs/projects" "$STORE_DIR/docs/decisions" "$STORE_DIR/docs/people" "$STORE_DIR/docs/intake"
  mkdir -p "$STORE_DIR/imports/chatgpt" "$STORE_DIR/imports/claude"
  mkdir -p "$STORE_DIR/prompts"
  echo "  Memory store initialized at $STORE_DIR"
fi

echo ""
echo "Done. Run /mogoj-show in Claude Code to verify."
