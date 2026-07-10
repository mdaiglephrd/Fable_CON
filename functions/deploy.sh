#!/usr/bin/env bash
# Stage and deploy the Azure Functions app.
#
# The app imports `common.*` and `ingest.*` from the repo root, so deployment
# stages those packages next to function_app.py in functions/.build/ and
# publishes from there. Nothing outside functions/.build/ is modified.
#
# Usage:
#   ./deploy.sh <function-app-name>
#   FUNCTION_APP_NAME=my-app ./deploy.sh
#
# Requires: Azure Functions Core Tools v4 (`func`) and an authenticated
# Azure CLI (`az login`). See the commented fallback at the bottom for a
# zip deploy that needs only the Azure CLI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$SCRIPT_DIR/.build"

APP_NAME="${1:-${FUNCTION_APP_NAME:-}}"
if [[ -z "$APP_NAME" ]]; then
    echo "usage: $0 <function-app-name>    (or set FUNCTION_APP_NAME)" >&2
    exit 2
fi

echo "Staging build directory: $BUILD_DIR"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

cp "$SCRIPT_DIR/function_app.py" \
   "$SCRIPT_DIR/processing.py" \
   "$SCRIPT_DIR/host.json" \
   "$SCRIPT_DIR/requirements.txt" \
   "$BUILD_DIR/"
cp -R "$REPO_ROOT/common" "$REPO_ROOT/ingest" "$BUILD_DIR/"

# Strip caches so they are not uploaded.
find "$BUILD_DIR" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$BUILD_DIR" -type f -name '*.pyc' -delete

echo "Publishing to function app: $APP_NAME"
(
    cd "$BUILD_DIR"
    func azure functionapp publish "$APP_NAME" --python
)

# --- Fallback without Core Tools (zip deploy; requires an existing app and
# --- SCM_DO_BUILD_DURING_DEPLOYMENT=true / ENABLE_ORYX_BUILD=true app settings
# --- so requirements.txt is installed server-side):
#
# RESOURCE_GROUP="my-resource-group"
# (cd "$BUILD_DIR" && zip -qr app.zip . -x 'app.zip')
# az functionapp deployment source config-zip \
#     --name "$APP_NAME" \
#     --resource-group "$RESOURCE_GROUP" \
#     --src "$BUILD_DIR/app.zip"

echo "Done."
