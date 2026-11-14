#!/bin/bash
# Copies /work/target into /src the way every harness build starts. Sourced by
# run_build.sh (plain and Foreman builds) and sandbox_phase.sh (prepare step),
# so the sandbox builds exactly the same tree.
# Copy the project into /src (works whether /src is a plain dir or a tmpfs mount).
mkdir -p /src
find /src -mindepth 1 -delete 2>/dev/null
cp -a /work/target/. /src/
rm -rf /src/build
# Build like a release tarball: drop the checkout's .git. Otherwise git's
# GIT-VERSION-GEN runs `git update-index --refresh` during compile, which reads
# every tracked file (all of t/, Documentation/, ...) and stamps mutants
# "-dirty" — noise for both Foreman's access logs and the output hashes.
# Set KEEP_GIT_DIR=1 to keep it.
[ -n "${KEEP_GIT_DIR:-}" ] || rm -rf /src/.git
# Make every build really process its wrap files: remove each wrap's extracted
# directory so `meson subprojects download` re-extracts it from the package
# cache (subprojects/packagecache), checking source_hash on the way. Without
# this Meson sees the extracted folders, logs "Already downloaded" and never
# reads the wrap, so wrap mutations change nothing ("dormant" mutants).
# Set KEEP_EXTRACTED_SUBPROJECTS=1 to skip.
if [ -z "${KEEP_EXTRACTED_SUBPROJECTS:-}" ]; then
  for w in /src/subprojects/*.wrap; do
    [ -f "$w" ] || continue
    # Only [wrap-file] wraps come back from packagecache; a [wrap-git] wrap's
    # directory may be vendored in the tree (GLib's gvdb), so leave it alone.
    grep -q '^\[wrap-file\]' "$w" || continue
    d=$(sed -n 's/^[[:space:]]*directory[[:space:]]*=[[:space:]]*//p' "$w" | head -1)
    case "$d" in ""|*/*|.|..) ;; *) rm -rf "/src/subprojects/$d" ;; esac
  done
fi
