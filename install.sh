#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Installing Playlistarr..."

sudo ln -sf "$ROOT/playlistarr.sh" /usr/local/bin/playlistarr

echo
echo "Playlistarr installed!"
echo "You can now run: playlistarr sync muchloud"
