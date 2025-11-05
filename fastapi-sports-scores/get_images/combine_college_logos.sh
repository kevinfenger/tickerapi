#!/bin/bash

# Script to combine college basketball and football logos, removing duplicates
# Creates a new 'college' directory with unique team logos

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPORT_LOGOS_DIR="$SCRIPT_DIR/sport_logos"
TEAM5_DIR="$SPORT_LOGOS_DIR/team5_logos"
TEAM6_DIR="$SPORT_LOGOS_DIR/team6_logos"
COLLEGE_DIR="$SPORT_LOGOS_DIR/college"

echo "Starting college logo combination and deduplication..."

# Check if source directories exist
if [ ! -d "$TEAM5_DIR" ]; then
    echo "Error: $TEAM5_DIR directory not found"
    exit 1
fi

if [ ! -d "$TEAM6_DIR" ]; then
    echo "Error: $TEAM6_DIR directory not found"
    exit 1
fi

# Create college directory
if [ -d "$COLLEGE_DIR" ]; then
    echo "Removing existing college directory..."
    rm -rf "$COLLEGE_DIR"
fi

mkdir -p "$COLLEGE_DIR"
echo "Created college directory: $COLLEGE_DIR"

# Function to count files in a directory
count_files() {
    local dir="$1"
    if [ -d "$dir" ]; then
        find "$dir" -name "*.bmp" | wc -l
    else
        echo "0"
    fi
}

# Count initial files
team5_count=$(count_files "$TEAM5_DIR")
team6_count=$(count_files "$TEAM6_DIR")
echo "Team5 (college basketball) logos: $team5_count"
echo "Team6 (college football) logos: $team6_count"

# Copy all team5 logos first (college basketball)
echo "Copying college basketball logos..."
cp "$TEAM5_DIR"/*.bmp "$COLLEGE_DIR/" 2>/dev/null
copied_from_team5=$(count_files "$COLLEGE_DIR")
echo "Copied $copied_from_team5 logos from college basketball"

# Copy team6 logos, but only if they don't already exist (avoid duplicates)
echo "Copying college football logos (avoiding duplicates)..."
duplicates_found=0
new_from_team6=0

for logo in "$TEAM6_DIR"/*.bmp; do
    if [ -f "$logo" ]; then
        filename=$(basename "$logo")
        if [ -f "$COLLEGE_DIR/$filename" ]; then
            echo "Duplicate found: $filename (skipping)"
            ((duplicates_found++))
        else
            cp "$logo" "$COLLEGE_DIR/"
            ((new_from_team6++))
        fi
    fi
done

# Final count
final_count=$(count_files "$COLLEGE_DIR")

echo ""
echo "=== SUMMARY ==="
echo "College basketball logos: $team5_count"
echo "College football logos: $team6_count"
echo "Total before deduplication: $((team5_count + team6_count))"
echo "Duplicates found and removed: $duplicates_found"
echo "New logos from football: $new_from_team6"
echo "Final unique college logos: $final_count"
echo ""
echo "College logos saved to: $COLLEGE_DIR"

# Show some example filenames
echo ""
echo "Sample college logos:"
ls "$COLLEGE_DIR"/*.bmp | head -10 | while read file; do
    echo "  $(basename "$file")"
done

if [ $final_count -gt 10 ]; then
    echo "  ... and $((final_count - 10)) more"
fi

echo ""
echo "Script completed successfully!"