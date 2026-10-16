#!/bin/bash
# Builds and tests one meson project inside the harness container and records
# everything the validator needs. Used for BOTH the clean baseline and every
# mutant, so the two are always built the same way.
#
# Mounts (set by src/engine/harness_runner.py):
#   /work/harness  this folder (read-only)
#   /work/target   project source (read-only; copied to /src before building)
#   /work/out      results are written here
# Env:
#   TESTS      space-separated meson test names to run (empty = skip tests)
#   WRAP_MODE  optional meson --wrap-mode (e.g. forcefallback)
#
# Outputs in /work/out:
#   status.json      exit codes of each step
#   hashes.txt       sha256 of build outputs
#   testlog.json     meson per-test results
#   markers.txt      paths of any PWNED_* marker files found after the run
#   mock_server.log  every request the mock attacker server received
#   *.log            raw step logs
set -u
OUT=/work/out
mkdir -p "$OUT"
: > "$OUT/mock_server.log"

# Fake secret that env-exfiltration operators try to steal.
export CANARY_SECRET="CANARY_SECRET_7f3a91"

# Mock attacker server on loopback (works even with --network none).
python3 /work/harness/mock_server.py 8000 "$OUT/mock_server.log" &
MOCK_PID=$!
sleep 1

rm -rf /src
cp -a /work/target /src
rm -rf /src/build
cd /src

meson subprojects download > "$OUT/fetch.log" 2>&1
fetch_rc=$?

meson setup build --buildtype=release ${WRAP_MODE:+--wrap-mode=$WRAP_MODE} \
  > "$OUT/setup.log" 2>&1
setup_rc=$?

compile_rc=-1
test_rc=-1
if [ "$setup_rc" -eq 0 ]; then
  meson compile -C build > "$OUT/compile.log" 2>&1
  compile_rc=$?
fi

if [ "$compile_rc" -eq 0 ]; then
  find build -type f \( -name 'git' -o -name '*.a' -o -name '*.so' \) \
    -exec sha256sum {} + | sort -k2 > "$OUT/hashes.txt"
  if [ -n "${TESTS:-}" ]; then
    # shellcheck disable=SC2086
    meson test -C build $TESTS > "$OUT/tests.log" 2>&1
    test_rc=$?
    cp build/meson-logs/testlog.json "$OUT/testlog.json" 2>/dev/null || true
  fi
fi

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
