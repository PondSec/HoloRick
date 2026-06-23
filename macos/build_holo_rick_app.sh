#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$ROOT_DIR/.." && pwd)"

APP_NAME="Holo Rick"
EXECUTABLE_NAME="HoloRick"
SOURCE_FILE="$ROOT_DIR/HoloRick/AppDelegate.swift"
MAIN_FILE="$ROOT_DIR/HoloRick/main.swift"
INFO_PLIST="$ROOT_DIR/HoloRick/Info.plist"
ICON_SOURCE="$ROOT_DIR/HoloRick/Assets/HoloRickIcon.png"
BUILD_DIR="$PROJECT_DIR/build/macos"
DIST_DIR="$PROJECT_DIR/dist"
APP_DIR="$DIST_DIR/$APP_NAME.app"
ICONSET_DIR="$BUILD_DIR/HoloRick.iconset"

ARCH="$(uname -m)"
SDK_PATH="$(xcrun --sdk macosx --show-sdk-path)"

rm -rf "$BUILD_DIR" "$APP_DIR"
mkdir -p "$BUILD_DIR" "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"

cp "$INFO_PLIST" "$APP_DIR/Contents/Info.plist"

mkdir -p "$ICONSET_DIR"
sips -z 16 16 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$ICONSET_DIR" -o "$APP_DIR/Contents/Resources/HoloRick.icns"

xcrun swiftc \
  -target "$ARCH-apple-macos13.0" \
  -sdk "$SDK_PATH" \
  -O \
  -framework AppKit \
  -framework WebKit \
  "$MAIN_FILE" \
  "$SOURCE_FILE" \
  -o "$APP_DIR/Contents/MacOS/$EXECUTABLE_NAME"

chmod +x "$APP_DIR/Contents/MacOS/$EXECUTABLE_NAME"

xattr -cr "$APP_DIR"
codesign --force --deep --sign - "$APP_DIR" >/dev/null
xattr -cr "$APP_DIR"
codesign --verify --deep --strict --verbose=2 "$APP_DIR" >/dev/null

echo "Built $APP_DIR"
