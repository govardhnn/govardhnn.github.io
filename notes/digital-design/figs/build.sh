#!/usr/bin/env bash
# Build every figs/src/*.tex into a same-named SVG in figs/.
# Requires: pdflatex (texlive + circuitikz), pdftocairo (poppler).
set -e
cd "$(dirname "$0")"
mkdir -p src
shopt -s nullglob
for tex in src/*.tex; do
  base=$(basename "$tex" .tex)
  echo "==> $base"
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory=src "$tex" > "src/$base.log" 2>&1 \
    || { echo "  FAILED — see src/$base.log"; tail -15 "src/$base.log"; continue; }
  pdftocairo -svg "src/$base.pdf" "$base.svg"
  echo "  -> $base.svg"
done
# tidy aux files
rm -f src/*.aux src/*.log src/*.pdf
echo "done."
