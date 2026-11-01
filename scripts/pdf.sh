#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
typst compile "$ROOT/thesis.typ" "$ROOT/thesis.pdf"
echo "Built: thesis.pdf"
