#!/bin/bash
# Clean-build baseline for a meson target.
# Builds on the container's own filesystem (not the Mac mount), so macOS
# file-system quirks can't affect the build or the tests.
set -e
rm -rf /src
cp -a /work/target /src                        # private copy inside the container
rm -rf /src/build
cd /src
meson subprojects download || true             # fetch deps while network is on
meson setup build --buildtype=release
meson compile -C build
# hashes first, so a failing test can't stop them being written
find build -type f \( -name 'git' -o -name '*.a' -o -name '*.so' \) \
  -exec sha256sum {} + | sort -k2 > /work/out/baseline_hashes.txt
meson test -C build t0000-basic t0001-init t1007-hash-object t-hash \
  > /work/out/baseline_tests.txt 2>&1 || echo "SOME TESTS FAILED - see baseline_tests.txt"
cp build/meson-logs/testlog.txt /work/out/baseline_testlog.txt
