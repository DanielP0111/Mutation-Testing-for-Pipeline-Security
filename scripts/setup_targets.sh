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
#                the rest are wrap-git). Build with
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

echo ""
echo "All targets ready in ${TARGETS_DIR}/"
ls -1 "${TARGETS_DIR}/"
