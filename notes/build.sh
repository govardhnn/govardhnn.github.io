#!/usr/bin/env bash
set -euo pipefail

MATHJAX="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OUTDIR=""
INPUTS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        -o) OUTDIR="$2"; shift 2 ;;
        -o*) OUTDIR="${1#-o}"; shift ;;
        *) INPUTS+=("$1"); shift ;;
    esac
done

[[ ${#INPUTS[@]} -ge 1 ]] || { echo "usage: $0 [-o OUTDIR] INPUT.md [INPUT.md ...]" >&2; exit 1; }

render() {
    local IN="$1"
    [[ -f "$IN" ]] || { echo "error: no such file: $IN" >&2; return 1; }

    local slug OUT
    slug="$(basename "$IN" .md | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')"
    OUT="${OUTDIR:-$SCRIPT_DIR}/$slug.html"
    mkdir -p "$(dirname "$OUT")"

    local TITLE
    TITLE="$(sed -n 's/^#[[:space:]]\+//p' "$IN" | head -1)"
    [[ -n "$TITLE" ]] || TITLE="$(basename "$IN" .md)"

    local TMP
    TMP="$(mktemp --suffix=.md)"

    gawk '
      function cap(s){ return toupper(substr(s,1,1)) substr(s,2) }
      BEGIN { inc = 0 }
      {
        if (inc == 0) {
          if (match($0, /^>[[:space:]]*\[!([A-Za-z]+)\][[:space:]]*(.*)$/, m)) {
            type = tolower(m[1]); title = (m[2] == "") ? cap(type) : m[2]
            cls = (type == "note" || type == "warning") ? type : "note"
            print ":::: {.callout ." cls "}\n::: callout-title\n" title "\n:::\n"
            inc = 1; next
          }
          print; next
        }
        if ($0 ~ /^>/) { line = $0; sub(/^>[[:space:]]?/, "", line); print line; next }
        print "::::"; inc = 0; print
      }
      END { if (inc == 1) print "::::" }
    ' "$IN" > "$TMP"

    pandoc "$TMP" \
        -f markdown+tex_math_dollars+pipe_tables+fenced_divs-yaml_metadata_block \
        -t html5 --standalone \
        --mathjax="$MATHJAX" \
        --toc --toc-depth=2 \
        --highlight-style=tango \
        -c "${NOTE_CSS:-../note-style.css}" \
        --metadata title="$TITLE" \
        -o "$OUT"
    rm -f "$TMP"

    sed -i '\#<script src="https://polyfill\.io#d' "$OUT"

    local FIGS_SRC nfigs=0
    FIGS_SRC="$(dirname "$IN")/figs"
    if [[ -d "$FIGS_SRC" ]]; then
        mkdir -p "$(dirname "$OUT")/figs"
        shopt -s nullglob nocaseglob
        for f in "$FIGS_SRC"/*.{svg,png,jpg,jpeg,gif}; do
            cp -p "$f" "$(dirname "$OUT")/figs/"
            nfigs=$((nfigs + 1))
        done
        shopt -u nullglob nocaseglob
    fi

    grep -q polyfill "$OUT" && { echo "error: polyfill line survived in $OUT" >&2; return 1; }
    echo "rendered: $IN -> $OUT  (${nfigs} figures synced)"
}

for f in "${INPUTS[@]}"; do
    render "$f"
done
