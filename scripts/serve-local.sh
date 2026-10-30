#!/usr/bin/env sh
# Serve the site locally with your Maps key injected, without touching the
# committed files. Usage: MAPS_API_KEY=... ./scripts/serve-local.sh [port]
set -eu
: "${MAPS_API_KEY:?Set MAPS_API_KEY in your environment}"
PORT="${1:-8000}"
BUILD="$(mktemp -d)"
cp -r public/. "$BUILD/"
sed -i.bak "s|__MAPS_API_KEY__|$MAPS_API_KEY|g" "$BUILD/index.html" && rm -f "$BUILD/index.html.bak"
echo "Serving $BUILD at http://localhost:$PORT"
cd "$BUILD" && python3 -m http.server "$PORT"
