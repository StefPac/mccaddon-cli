#!/bin/bash
# Packages addon into .mcaddon and .mcpack files

ADDON_PATH=$1
OUTPUT_DIR=$2
ADDON_NAME=$(basename "$ADDON_PATH")

if [ -z "$ADDON_PATH" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: ./package-addon.sh <addon_path> <output_dir>"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
TEMP_DIR=$(mktemp -d)

# Copy packs to temp
[ -d "$ADDON_PATH/behavior_pack" ] && cp -r "$ADDON_PATH/behavior_pack" "$TEMP_DIR/"
[ -d "$ADDON_PATH/resource_pack" ] && cp -r "$ADDON_PATH/resource_pack" "$TEMP_DIR/"

# Create .mcaddon (both packs)
cd "$TEMP_DIR"
zip -r "$OUTPUT_DIR/${ADDON_NAME}.mcaddon" ./* >/dev/null 2>&1

# Create individual .mcpack files
if [ -d "behavior_pack" ]; then
    cd behavior_pack
    zip -r "$OUTPUT_DIR/${ADDON_NAME}_BP.mcpack" ./* >/dev/null 2>&1
    cd ..
fi

if [ -d "resource_pack" ]; then
    cd resource_pack
    zip -r "$OUTPUT_DIR/${ADDON_NAME}_RP.mcpack" ./* >/dev/null 2>&1
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo "$OUTPUT_DIR/${ADDON_NAME}.mcaddon"
