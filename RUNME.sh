#!/usr/bin/env bash

# Run from the repo root, i.e.:
#   ./RUNME.sh

rm -rf ./gen

./src/main/validate.sh --data-root ../data-exports

./src/main/extract_files.sh --data-root ../data-exports
./src/main/extract_heredocs.sh --data-root ../data-exports

./src/main/infer_tables.sh --data-root ../data-exports
#   NB the above call requires an Anthropic API key and costs money.
./src/main/present.sh --data-root ../data-exports
