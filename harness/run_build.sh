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
#   SETUP_ARGS    optional extra meson setup args (e.g. --force-fallback-for=pcre2,zlib)
#   FETCH_SUBPROJECTS  optional subprojects to download (default: all)
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

# Copy the project into /src (shared with the sandbox; see prepare_src.sh).
. /work/harness/prepare_src.sh
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
