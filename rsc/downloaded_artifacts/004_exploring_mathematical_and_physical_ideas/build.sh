#!/bin/bash
# Build all papers and place PDFs in ./output/
set -e

mkdir -p output

echo "Building Paper 1..."
python paper1_v5.py
mv paper1_v4.pdf output/paper1_v5.pdf
echo "  -> output/paper1_v5.pdf"

echo "Building Paper 2..."
python paper2_v4.py
mv paper2_v4.pdf output/paper2_v4.pdf
echo "  -> output/paper2_v4.pdf"

echo "Done."
