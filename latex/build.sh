#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -d /workspace/.texlive/usr/share/texlive/texmf-dist ]; then
  export TEXMFHOME=/workspace/.texlive/usr/share/texlive/texmf-dist
fi
export TEXMFVAR="${TEXMFVAR:-$PWD/build/texmf-var}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$PWD/build/cache}"
mkdir -p build "$TEXMFVAR" "$XDG_CACHE_HOME"
latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error \
  -outdir=build main.tex
cp build/main.pdf thesis.pdf
