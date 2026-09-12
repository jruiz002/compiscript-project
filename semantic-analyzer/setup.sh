#!/usr/bin/env bash
# setup.sh — One-time setup for Compiscript compiler
# Run this script from the project root directory AFTER installing dependencies.

set -e

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

ok()   { echo -e "${GREEN}  ✓ $1${RESET}"; }
info() { echo -e "  → $1"; }
warn() { echo -e "${YELLOW}  ⚠ $1${RESET}"; }
err()  { echo -e "${RED}  ✗ $1${RESET}"; }

echo ""
echo -e "${BOLD}══════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  Compiscript Compiler — Setup${RESET}"
echo -e "${BOLD}══════════════════════════════════════════════${RESET}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATED_DIR="$PROJECT_ROOT/compiler/generated"
ANTLR_JAR="$PROJECT_ROOT/antlr-4.13.2-complete.jar"
ANTLR_URL="https://www.antlr.org/download/antlr-4.13.2-complete.jar"

# ── Step 1: Check/Download ANTLR4 jar ─────────────────────────────
echo ""
info "Step 1: ANTLR4 tool jar"
if [ ! -f "$ANTLR_JAR" ]; then
  info "Downloading antlr-4.13.2-complete.jar..."
  if curl -sSL "$ANTLR_URL" -o "$ANTLR_JAR" 2>/dev/null; then
    ok "Downloaded antlr-4.13.2-complete.jar"
  else
    err "Download failed. Please manually download:"
    echo "    $ANTLR_URL"
    echo "    and place it at: $ANTLR_JAR"
    exit 1
  fi
else
  ok "antlr-4.13.2-complete.jar already present"
fi

# ── Step 2: Check Java ────────────────────────────────────────────
echo ""
info "Step 2: Java runtime"
if java -version 2>&1 | grep -q "version"; then
  JAVA_VER=$(java -version 2>&1 | head -1)
  ok "Java found: $JAVA_VER"
else
  err "Java not found. Install JDK 11+ from https://adoptium.net/"
  exit 1
fi

# ── Step 3: Python dependencies ───────────────────────────────────
echo ""
info "Step 3: Python dependencies"

# Try to use a virtualenv if available
VENV_DIR="$PROJECT_ROOT/.venv"
if [ -f "$VENV_DIR/bin/python3" ]; then
  PYTHON="$VENV_DIR/bin/python3"
  PIP="$VENV_DIR/bin/pip3"
  ok "Using virtualenv at .venv"
else
  PYTHON="python3"
  PIP="pip3"
fi

install_pkg() {
  local pkg="$1"
  local import_name="${2:-$1}"
  if $PYTHON -c "import $import_name" 2>/dev/null; then
    ok "$pkg already installed"
  else
    info "Installing $pkg..."
    $PIP install "$pkg" --break-system-packages 2>/dev/null || \
    $PIP install "$pkg" --user 2>/dev/null || \
    $PIP install "$pkg" 2>/dev/null || \
    { err "Failed to install $pkg. Run: pip install $pkg"; return 1; }
    ok "$pkg installed"
  fi
}

install_pkg "antlr4-python3-runtime==4.13.2" "antlr4"
install_pkg "flask" "flask"
install_pkg "flask-cors" "flask_cors"
install_pkg "graphviz" "graphviz"

# ── Step 4: Generate ANTLR4 parser ────────────────────────────────
echo ""
info "Step 4: Generating ANTLR4 parser files"
mkdir -p "$GENERATED_DIR"

java -jar "$ANTLR_JAR" \
  -Dlanguage=Python3 \
  -visitor \
  -listener \
  -o "$GENERATED_DIR" \
  "$PROJECT_ROOT/compiler/Compiscript.g4"

# Create __init__.py
touch "$GENERATED_DIR/__init__.py"

ok "Parser generated in compiler/generated/"
ls "$GENERATED_DIR"/*.py 2>/dev/null | while read f; do echo "      • $(basename "$f")"; done

# ── Step 5: Verify ────────────────────────────────────────────────
echo ""
info "Step 5: Sanity check"
$PYTHON -c "
import os, sys
# ANTLR emits into compiler/generated/ or compiler/generated/compiler/ depending on version
for p in ['compiler/generated', 'compiler/generated/compiler']:
    if os.path.isfile(os.path.join(p, 'CompiscriptLexer.py')):
        sys.path.insert(0, p)
        break
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
print('  ✓ Parser imported successfully')
" && ok "All imports working"

echo ""
echo -e "${BOLD}══════════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  ✓ Setup complete!${RESET}"
echo -e "${BOLD}══════════════════════════════════════════════${RESET}"
echo ""
echo "  Analyze a file:"
echo "    python3 compiler/driver.py program/program.cps"
echo ""
echo "  Run tests:"
echo "    python3 tests/run_tests.py"
echo ""
echo "  Launch IDE:"
echo "    python3 ide/server.py"
echo "    → http://localhost:5000"
echo ""
