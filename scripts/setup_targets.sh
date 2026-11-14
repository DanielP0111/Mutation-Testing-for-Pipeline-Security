#!/usr/bin/env bash
# scripts/setup_targets.sh
#
# Clone the target Meson projects at pinned versions into data/targets/.
# Safe to re-run — skips any project that already has files present.
#
# Usage:
#   bash scripts/setup_targets.sh
#
# Requirements:
#   git (any recent version)
#
# Target projects:
#   git    — Git v2.48.0   (primary target; 5 .wrap files)
#   numpy  — NumPy v2.0.0  (Meson, but NO .wrap files; needs its vendored Meson fork + Cython)
#   scipy  — SciPy v1.14.0 (Meson, but NO .wrap files)
#   gnome-glib — GLib 2.80.0 (second target; plain C; wrap-file: pcre2, zlib;
#                the rest are wrap-git; zlib.wrap swapped to 1.3.1 below). Build with
#                --setup-args=--force-fallback-for=pcre2,zlib --fetch-subprojects='pcre2 zlib'

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGETS_DIR="${REPO_ROOT}/data/targets"

mkdir -p "${TARGETS_DIR}"

clone_at_tag() {
    local name="$1"
    local url="$2"
    local tag="$3"
    local dest="${TARGETS_DIR}/${name}"

    if [ -d "${dest}" ] && [ -n "$(ls -A "${dest}" 2>/dev/null)" ]; then
        echo "[skip] ${name} already present at ${dest}"
        return 0
    fi

    echo "[clone] ${name} @ ${tag} → ${dest}"
    # NumPy and SciPy vendor parts of their build (incl. NumPy's Meson fork)
    # as git submodules; without them the tree does not configure.
    git clone \
        --depth 1 \
        --branch "${tag}" \
        --single-branch \
        --recurse-submodules --shallow-submodules \
        "${url}" \
        "${dest}"
    echo "[done]  ${name}"
}

# ---------------------------------------------------------------------------
# Git v2.48.0  (primary target)
# Wrap files:  git/subprojects/*.wrap. The harness builds offline, so after
# cloning, fill the package cache once (needs meson + network):
#   (cd data/targets/git && meson subprojects download)
# ---------------------------------------------------------------------------
clone_at_tag \
    "git" \
    "https://github.com/git/git.git" \
    "v2.48.0"

# ---------------------------------------------------------------------------
# NumPy v2.0.0
# Meson build: numpy/meson.build  (top-level)
# Wrap files:  numpy/subprojects/*.wrap
# ---------------------------------------------------------------------------
clone_at_tag \
    "numpy" \
    "https://github.com/numpy/numpy.git" \
    "v2.0.0"

# ---------------------------------------------------------------------------
# SciPy v1.14.0
# Meson build: scipy/meson.build
# Wrap files:  scipy/subprojects/*.wrap
# ---------------------------------------------------------------------------
clone_at_tag \
    "scipy" \
    "https://github.com/scipy/scipy.git" \
    "v1.14.0"

# ---------------------------------------------------------------------------
# GLib v2.80.0  (GNOME core utility library — well-established Meson project)
# Meson build: gnome-glib/meson.build
# Wrap files:  gnome-glib/subprojects/*.wrap
# ---------------------------------------------------------------------------
# Official GitHub mirror: gitlab.gnome.org rejects scripted clones (HTTP 406).
clone_at_tag \
    "gnome-glib" \
    "https://github.com/GNOME/glib.git" \
    "2.80.0"

# GLib 2.80.0 pins zlib 1.2.11 from zlib.net/fossils, which no longer serves a
# tarball matching the pinned hash (hash mismatch, Nov 14). Swap in the same
# zlib 1.3.1 wrap the git target uses (WrapDB, with a GitHub fallback URL).
cp "${TARGETS_DIR}/git/subprojects/zlib.wrap" "${TARGETS_DIR}/gnome-glib/subprojects/zlib.wrap" 2>/dev/null || \
cat > "${TARGETS_DIR}/gnome-glib/subprojects/zlib.wrap" <<'WRAP'
[wrap-file]
directory = zlib-1.3.1
source_url = http://zlib.net/fossils/zlib-1.3.1.tar.gz
source_fallback_url = https://github.com/mesonbuild/wrapdb/releases/download/zlib_1.3.1-1/zlib-1.3.1.tar.gz
source_filename = zlib-1.3.1.tar.gz
source_hash = 9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23
patch_filename = zlib_1.3.1-1_patch.zip
patch_url = https://wrapdb.mesonbuild.com/v2/zlib_1.3.1-1/get_patch
patch_hash = e79b98eb24a75392009cec6f99ca5cdca9881ff20bfa174e8b8926d5c7a47095
wrapdb_version = 1.3.1-1

[provide]
zlib = zlib_dep
WRAP

echo ""
echo "All targets ready in ${TARGETS_DIR}/"
ls -1 "${TARGETS_DIR}/"
