#!/bin/bash
# Builds and tests one meson project inside the harness container and records
# everything the validator needs. Used for BOTH the clean baseline and every
# mutant, so the two are always built the same way.
#
# Mounts (set by src/engine/harness_runner.py):
#   /work/harness  this folder (read-only)
#   /work/target   project source (read-only; copied to /src before building)
#   /work/out      results are written here
#   /work/foreman  vendored Foreman (read-only; only when FOREMAN_SPEC is set)
# Env:
#   TESTS         space-separated meson test names to run (empty = skip tests)
#   WRAP_MODE     optional meson --wrap-mode (e.g. forcefallback)
#   FOREMAN_SPEC  optional path to a Foreman phase spec; when set, the four
#                 steps run as Foreman build phases (see harness/step.sh) and
#                 /src must be mounted with strictatime (harness_runner does it)
#
# Outputs in /work/out:
#   status.json      exit codes of each step
#   hashes.txt       sha256 of build outputs
#   testlog.json     meson per-test results
#   markers.txt      paths of any PWNED_* marker files found after the run
#   mock_server.log  every request the mock attacker server received
#   *.log            raw step logs
#   foreman_info.txt / foreman_warnings.txt   (Foreman runs only)
set -u
OUT=/work/out
mkdir -p "$OUT"
: > "$OUT/mock_server.log"
rm -f "$OUT"/*.rc

# Fake secret that env-exfiltration operators try to steal.
export CANARY_SECRET="CANARY_SECRET_7f3a91"

# Mock attacker server on loopback (works even with --network none).
python3 /work/harness/mock_server.py 8000 "$OUT/mock_server.log" &
MOCK_PID=$!
sleep 1

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
    d=$(sed -n 's/^[[:space:]]*directory[[:space:]]*=[[:space:]]*//p' "$w" | head -1)
    case "$d" in ""|*/*|.|..) ;; *) rm -rf "/src/subprojects/$d" ;; esac
  done
fi
cd /src

if [ -n "${FOREMAN_SPEC:-}" ]; then
  python3 - "$FOREMAN_SPEC" /src/build_phases.json <<'PY'
import json, sys
spec = json.load(open(sys.argv[1]))
phases = []
for name in ("fetch", "setup", "compile", "test"):
    p = {"name": name, "commands": [["bash", "/work/harness/step.sh", name]]}
    perms = spec.get("phases", {}).get(name)
    if perms:
        p["permissions"] = perms
    phases.append(p)
json.dump(phases, open(sys.argv[2], "w"), indent=2)
PY
  cp /src/build_phases.json "$OUT/foreman_build_phases.json"
  awk '$2=="/src"{print $4}' /proc/mounts > "$OUT/foreman_mount_opts.txt"
  python3 /work/harness/foreman_launch.py -C /src \
    -oi "$OUT/foreman_info.txt" -ow "$OUT/foreman_warnings.txt" > "$OUT/foreman.log" 2>&1
  echo $? > "$OUT/foreman.rc"
else
  for step in fetch setup compile test; do
    bash /work/harness/step.sh "$step"
  done
fi

rc() { cat "$OUT/$1.rc" 2>/dev/null || echo -1; }
fetch_rc=$(rc fetch); setup_rc=$(rc setup); compile_rc=$(rc compile); test_rc=$(rc test)

# Marker files a mutant may have dropped anywhere it could write.
find /src /tmp /root -name 'PWNED_*' 2>/dev/null | sort > "$OUT/markers.txt"

kill "$MOCK_PID" 2>/dev/null

python3 - "$OUT/status.json" "$fetch_rc" "$setup_rc" "$compile_rc" "$test_rc" <<'PY'
import json, sys
path, fetch, setup, comp, test = sys.argv[1], *map(int, sys.argv[2:])
json.dump({"fetch_rc": fetch, "setup_rc": setup, "compile_rc": comp,
           "test_rc": test}, open(path, "w"), indent=2)
PY
echo "harness run finished: setup=$setup_rc compile=$compile_rc tests=$test_rc"
