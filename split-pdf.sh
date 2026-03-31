#!/bin/bash

# Split all PDFs in temp-data/ into individual pages under pdfdata/{category}/
# Fully automatic — icons, subtitles, level labels all handled.
# Just drop PDFs in temp-data/ and run: bash split-pdf.sh

SOURCE_DIR="temp-data"
OUTPUT_DIR="pdfdata"
DATA_JS="$OUTPUT_DIR/data.js"

# Auto-detect icon and subtitle from folder name
get_icon_and_subtitle() {
    case "$1" in
        automation)   echo "🏭|Hi-Speed Doors, Boom Barriers & Shutters" ;;
        biomass)      echo "🌿|Boilers, Pellets & Feedstock" ;;
        renewable)    echo "🔆|Solar Panels, Inverters & Accessories" ;;
        metal*)       echo "💪|TMT, Wire Rod, HRPO, Structural Steel" ;;
        electrical*)  echo "⚡|Cables, Panels, Switches & Lights" ;;
        crash*)       echo "🛡️|W-Beam, Thrie-Beam & Road Safety" ;;
        structural*)  echo "🏗️|MS Plates, Beams, Channels & Angles" ;;
        solar)        echo "🔆|Solar Panels, Inverters & Accessories" ;;
        safety)       echo "🛡️|Road Safety & Signage" ;;
        conveyor)     echo "🏭|Belt, Roller & Chain Systems" ;;
        *)            echo "📦|Learning Journey" ;;
    esac
}

# Auto-detect level labels by reading each PDF page title
get_level_labels() {
    local PDF_PATH="$1"
    local PAGE_COUNT="$2"
    local LABELS=""

    for i in $(seq 1 $PAGE_COUNT); do
        # Extract text from page, find "Level X" or "Level X.X" pattern
        PAGE_TEXT=$(pdftotext -f $i -l $i "$PDF_PATH" - 2>/dev/null | head -5)
        LVL=$(echo "$PAGE_TEXT" | grep -oi 'level [0-9]\+\(\.[0-9]\+\)\?' | head -1)

        if [ -z "$LVL" ]; then
            LVL="Level $i"
        else
            # Capitalize properly
            LVL=$(echo "$LVL" | sed 's/level/Level/i')
        fi

        if [ -z "$LABELS" ]; then
            LABELS="$LVL"
        else
            LABELS="$LABELS|$LVL"
        fi
    done
    echo "$LABELS"
}

echo "var pfFolders = {" > "$DATA_JS"
FIRST=true

for PDF in "$SOURCE_DIR"/*.pdf "$SOURCE_DIR"/*.PDF; do
    [ -f "$PDF" ] || continue

    NAME=$(basename "$PDF" .pdf)
    NAME=$(basename "$NAME" .PDF)

    FOLDER=$(echo "$NAME" | sed 's/ - .*//' | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g;s/[^a-z0-9\-]//g')
    LABEL=$(echo "$NAME" | sed 's/ - .*//')

    PAGES=$(pdfinfo "$PDF" 2>/dev/null | grep "Pages:" | awk '{print $2}')
    [ -z "$PAGES" ] && echo "SKIP: $PDF" && continue

    mkdir -p "$OUTPUT_DIR/$FOLDER"
    pdfseparate "$PDF" "$OUTPUT_DIR/$FOLDER/page-%d.pdf"

    # Get icon and subtitle
    ICON_SUB=$(get_icon_and_subtitle "$FOLDER")
    ICON=$(echo "$ICON_SUB" | cut -d'|' -f1)
    SUBTITLE=$(echo "$ICON_SUB" | cut -d'|' -f2)

    # Get level labels from PDF content
    LEVEL_LABELS=$(get_level_labels "$PDF" "$PAGES")

    echo "$NAME -> $OUTPUT_DIR/$FOLDER/ ($PAGES pages) $ICON"

    if [ "$FIRST" = true ]; then FIRST=false; else echo "," >> "$DATA_JS"; fi

    printf '  "%s": {\n' "$FOLDER" >> "$DATA_JS"
    printf '    label: "%s",\n' "$LABEL" >> "$DATA_JS"
    printf '    icon: "%s",\n' "$ICON" >> "$DATA_JS"
    printf '    subtitle: "%s",\n' "$SUBTITLE" >> "$DATA_JS"
    printf '    pages: [\n' >> "$DATA_JS"
    for i in $(seq 1 $PAGES); do
        COMMA=","; [ $i -eq $PAGES ] && COMMA=""
        LVL=$(echo "$LEVEL_LABELS" | cut -d'|' -f$i)
        [ -z "$LVL" ] && LVL="Level $i"
        printf '      { page: %d, label: "%s", pdf: "page-%d.pdf" }%s\n' "$i" "$LVL" "$i" "$COMMA" >> "$DATA_JS"
    done
    printf '    ]\n  }' >> "$DATA_JS"
done

echo "" >> "$DATA_JS"
echo "};" >> "$DATA_JS"

echo ""
echo "Done."
cat "$DATA_JS"
