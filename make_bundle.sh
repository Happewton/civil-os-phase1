#!/usr/bin/env bash
# Package the CIVIL-OS Phase-1 prototype into a downloadable zip.
set -e
zip -r civil-os-phase1.zip README.md IMPLEMENTATION_NOTES.md pyproject.toml \
    demo.py run_tests.sh make_bundle.sh civil_os tests
echo "Created civil-os-phase1.zip"
