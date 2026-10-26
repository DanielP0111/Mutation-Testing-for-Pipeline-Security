#!/usr/bin/env python3
"""Baseline defense: Meson .wrap integrity / source pinning check.

A lightweight outside baseline (no PipelineSave code required). It verifies
each subprojects/*.wrap in a candidate tree against a trusted manifest:
  - source_url host must be on the allowlist
  - source_hash must equal the trusted hash for that source_filename
A wrap that fails either check is FLAGGED; the defense BLOCKS the build if any
wrap is flagged. Use --learn once on a clean target to emit the manifest.

Usage:
  learn:  wrap_integrity_check.py --learn --target <clean_tree> --manifest m.json
  check:  wrap_integrity_check.py --target <candidate_tree> --manifest m.json [--json]

Exit codes: 0 = allowed (no flags), 1 = blocked (>=1 flag), 2 = usage/error.
"""
import argparse, glob, json, os, re, sys
from urllib.parse import urlparse

FIELDS = ("source_url", "source_fallback_url", "source_hash", "source_filename")

def parse_wrap(path):
    out = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"\s*([A-Za-z_]+)\s*=\s*(.+?)\s*$", line)
        if m and m.group(1) in FIELDS:
            out[m.group(1)] = m.group(2)
    return out

def wraps(target):
    return sorted(glob.glob(os.path.join(target, "subprojects", "*.wrap")))

def learn(target):
    allow, pins = set(), {}
    for w in wraps(target):
        d = parse_wrap(w)
        for k in ("source_url", "source_fallback_url"):
            if d.get(k):
                h = urlparse(d[k]).hostname
                if h:
                    allow.add(h)
        if d.get("source_filename") and d.get("source_hash"):
            pins[d["source_filename"]] = d["source_hash"]
    return {"allowed_hosts": sorted(allow), "pinned_hashes": pins}

def check(target, manifest):
    allow = set(manifest.get("allowed_hosts", []))
    pins = manifest.get("pinned_hashes", {})
    flags = []
    for w in wraps(target):
        name = os.path.basename(w)
        d = parse_wrap(w)
        url = d.get("source_url", "")
        host = urlparse(url).hostname if url else None
        if host and host not in allow:
            flags.append({"wrap": name, "reason": "url_host_not_allowlisted",
                          "detail": host})
        fn, h = d.get("source_filename"), d.get("source_hash")
        if fn in pins:
            if not h:
                flags.append({"wrap": name, "reason": "source_hash_removed",
                              "detail": fn})
            elif h != pins[fn]:
                flags.append({"wrap": name, "reason": "source_hash_mismatch",
                              "detail": fn})
    return flags

def main():
    ap = argparse.ArgumentParser(description="Meson wrap integrity / pinning defense")
    ap.add_argument("--target", required=True, help="Meson project tree to inspect")
    ap.add_argument("--manifest", required=True, help="trusted manifest JSON path")
    ap.add_argument("--learn", action="store_true", help="emit manifest from clean --target")
    ap.add_argument("--json", action="store_true", help="print machine-readable result")
    a = ap.parse_args()
    if a.learn:
        json.dump(learn(a.target), open(a.manifest, "w"), indent=2, sort_keys=True)
        print(f"wrote manifest: {a.manifest}")
        return 0
    if not os.path.exists(a.manifest):
        print(f"manifest not found: {a.manifest} (run --learn first)", file=sys.stderr)
        return 2
    flags = check(a.target, json.load(open(a.manifest)))
    blocked = bool(flags)
    if a.json:
        print(json.dumps({"defense": "wrap_integrity_check",
                          "blocked": blocked, "flags": flags}, indent=2))
    else:
        print(f"[wrap_integrity_check] {'BLOCKED' if blocked else 'ALLOWED'}"
              + ("" if not flags else ": " + "; ".join(
                  f"{f['wrap']} {f['reason']} ({f['detail']})" for f in flags)))
    return 1 if blocked else 0

if __name__ == "__main__":
    sys.exit(main())
