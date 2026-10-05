#!/usr/bin/bash
# Installs SimpleDeckyTDP for ONEXPLAYER 3 (raicoll/SimpleDeckyTDP-OXP3_custom).
# Requires Decky Loader. Replaces an existing SimpleDeckyTDP install.

set -e

REPO="raicoll/SimpleDeckyTDP-OXP3_custom"
VERSION=${VERSION:-"LATEST"}
PLUGIN_DIR="$HOME/homebrew/plugins"

if [ "$EUID" -eq 0 ]; then
  echo "Please do not run as root"
  exit 1
fi

if [ ! -d "$PLUGIN_DIR" ]; then
  echo "Decky Loader is not installed ($PLUGIN_DIR not found)"
  exit 1
fi

API_URL="https://api.github.com/repos/$REPO/releases/latest"
if [ "$VERSION" != "LATEST" ]; then
  API_URL="https://api.github.com/repos/$REPO/releases/tags/$VERSION"
fi

ZIP_URL=$(curl -s "$API_URL" | grep "browser_download_url" | grep "\.zip" | head -n 1 | cut -d '"' -f 4)
if [ -z "$ZIP_URL" ]; then
  echo "Could not find a release to download"
  exit 1
fi

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Downloading $ZIP_URL"
curl -L "$ZIP_URL" -o "$TMP_DIR/SimpleDeckyTDP.zip"

echo "Removing the previous SimpleDeckyTDP install if it exists"
sudo rm -rf "$PLUGIN_DIR/SimpleDeckyTDP"

echo "Installing"
if command -v unzip >/dev/null; then
  sudo unzip -q "$TMP_DIR/SimpleDeckyTDP.zip" -d "$PLUGIN_DIR"
else
  sudo 7z x "$TMP_DIR/SimpleDeckyTDP.zip" -o"$PLUGIN_DIR"
fi

sudo systemctl restart plugin_loader.service

if [ -d "$PLUGIN_DIR/PowerTools" ]; then
  echo "Note: PowerTools is installed. It also controls TDP, so disable or remove it in Decky."
fi

echo "Installation complete"
