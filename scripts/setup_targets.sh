#!/usr/bin/env bash
# scripts/setup_targets.sh
#
# Clone the three target Meson projects at pinned versions into data/targets/.
# Safe to re-run — skips any project that already has files present.
#
# Usage:
#   bash scripts/setup_targets.sh
#
# Requirements:
#   git (any recent version)
#
# Target projects:
#   numpy  — NumPy v2.0.0  (migrated to Meson in 1.25; many .wrap files)
#   scipy  — SciPy v1.14.0 (migrated to Meson in 1.9;  many .wrap files)
#   gnome  — GLib v2.80.0  (mature Meson project; platform .wrap files)

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
    git clone \
        --depth 1 \
        --branch "${tag}" \
        --single-branch \
        "${url}" \
        "${dest}"
    echo "[done]  ${name}"
}

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
clone_at_tag \
    "gnome-glib" \
    "https://gitlab.gnome.org/GNOME/glib.git" \
    "2.80.0"

echo ""
echo "All targets ready in ${TARGETS_DIR}/"
ls -1 "${TARGETS_DIR}/"
