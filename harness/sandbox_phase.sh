#!/bin/bash
# Per-phase isolation sandbox: ONE container per call, started by
# src/engine/sandbox.py. Our own design (not PipelineSave's sandbox).
#
#   sandbox_phase.sh prepare|fetch|setup|compile|test|finish
#
# Each build phase gets a fresh container: its own /tmp (tmpfs, discarded when
# the phase ends), no network, and no Linux capabilities for the build itself.
# The only state shared between phases is /src, a Docker volume. In it:
#   - the build step runs as the unprivileged `builder` user (uid 1000);
#   - /src is root-owned and read-only to builder, EXCEPT build/ and the paths
#     the policy says this phase wrote in the clean build.
# This script's own work (setting ownership, observing evidence) runs as root
# before and after the build step; builder's processes are killed in between.
#
# Mounts:  /src volume (shared) | /work/harness ro | /work/out results (root)
#          /work/target ro (prepare only) | /work/policy.json ro (enforce only;
#          absent = LEARN mode: all of /src writable, writes are recorded)
# Env:     TESTS, WRAP_MODE, SETUP_ARGS, FETCH_SUBPROJECTS (as harness/run_build.sh)
#
# Per phase it writes to /work/out:
#   <phase>.log/.rc (and hashes.txt, testlog.json, tests.log for test)
#   sandbox_<phase>_markers.txt   PWNED_* files present INSIDE the phase
#                                 (/src, its private /tmp, /root, /home)
#   sandbox_<phase>_requests.log  requests the in-phase mock server received
#   sandbox_<phase>_changes.json  what the phase changed in /src outside build/
# finish writes markers.txt (PWNED_* left in /src, i.e. what outlived the
# phases) and status.json.
set -u
PHASE="$1"
OUT=/work/out
POLICY=/work/policy.json
B_UID=1000; B_GID=1000
mkdir -p "$OUT"

case "$PHASE" in
  prepare)
    . /work/harness/prepare_src.sh
    exit 0 ;;
  finish)
    find /src -name 'PWNED_*' 2>/dev/null | sort > "$OUT/markers.txt"
    rc() { cat "$OUT/$1.rc" 2>/dev/null || echo -1; }
    python3 - "$OUT/status.json" "$(rc fetch)" "$(rc setup)" "$(rc compile)" "$(rc test)" <<'PY'
import json, sys
path, *rcs = sys.argv[1:]
json.dump(dict(zip(("fetch_rc", "setup_rc", "compile_rc", "test_rc"), map(int, rcs))),
          open(path, "w"), indent=2)
PY
    exit 0 ;;
  fetch|setup|compile|test) ;;
  *) echo "unknown phase: $PHASE" >&2; exit 2 ;;
esac

# --- 1. Lock /src, then open what this phase may write -----------------------
chown -R 0:0 /src
chmod -R u+rwX,go+rX,go-w /src
mkdir -p /src/build
chown -R "$B_UID:$B_GID" /src/build
if [ -f "$POLICY" ]; then
  python3 - "$POLICY" "$PHASE" "$B_UID" "$B_GID" <<'PY'
import json, os, sys
policy, phase, uid, gid = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
p = json.load(open(policy)).get("phases", {}).get(phase, {})
# write_files: existing files the phase rewrote in the clean build.
# create_in:   directories it created new entries in (only the dir itself is
#              opened, so builder can add entries there, not edit siblings).
for rel in p.get("write_files", []):
    path = os.path.join("/src", rel)
    if os.path.lexists(path) and not os.path.islink(path):
        os.chown(path, uid, gid)
for rel in p.get("create_in", []):
    path = os.path.normpath(os.path.join("/src", rel))
    os.makedirs(path, exist_ok=True)
    os.chown(path, uid, gid)
PY
else
  chown -R "$B_UID:$B_GID" /src   # learn mode
fi

# --- 2. Snapshot, mock attacker, run the step as builder ---------------------
find /src -path /src/build -prune -o -print | sort > /tmp/.sbx_before
PHASE_OUT=/tmp/phase_out
mkdir -p "$PHASE_OUT" /tmp/home
cp "$OUT"/*.rc "$PHASE_OUT"/ 2>/dev/null   # step.sh reads earlier phases' rc
chown -R "$B_UID:$B_GID" "$PHASE_OUT" /tmp/home
: > "$OUT/sandbox_${PHASE}_requests.log"
python3 /work/harness/mock_server.py 8000 "$OUT/sandbox_${PHASE}_requests.log" &
MOCK_PID=$!
sleep 1
touch /tmp/.sbx_stamp

as_builder() {
  setpriv --reuid="$B_UID" --regid="$B_GID" --clear-groups --inh-caps=-all \
    env -i PATH="$PATH" HOME=/tmp/home OUT="$PHASE_OUT" \
        CANARY_SECRET="CANARY_SECRET_7f3a91" \
        TESTS="${TESTS:-}" WRAP_MODE="${WRAP_MODE:-}" SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-}" \
        SETUP_ARGS="${SETUP_ARGS:-}" FETCH_SUBPROJECTS="${FETCH_SUBPROJECTS:-}" \
        "$@"
}
as_builder bash /work/harness/step.sh "$PHASE"
as_builder bash -c 'kill -9 -1' 2>/dev/null   # nothing the payload started survives

# --- 3. Record results and evidence (as root) --------------------------------
for f in "$PHASE.log" "$PHASE.rc" hashes.txt testlog.json tests.log; do
  [ -f "$PHASE_OUT/$f" ] && cp "$PHASE_OUT/$f" "$OUT/$f"
done
[ -f "$OUT/$PHASE.rc" ] || echo -1 > "$OUT/$PHASE.rc"
find /src /tmp /root /home -name 'PWNED_*' 2>/dev/null | sort > "$OUT/sandbox_${PHASE}_markers.txt"
find /src -path /src/build -prune -o -cnewer /tmp/.sbx_stamp -print | sort > /tmp/.sbx_changed
python3 - /tmp/.sbx_before /tmp/.sbx_changed "$OUT/sandbox_${PHASE}_changes.json" <<'PY'
import json, os, sys
before = set(open(sys.argv[1]).read().split("\n")) - {""}
changed = set(open(sys.argv[2]).read().split("\n")) - {"", "/src"}
rel = lambda p: os.path.relpath(p, "/src")
modified, created = [], set()
for p in sorted(changed):
    if p in before:
        if not os.path.isdir(p):   # a dir's ctime moves whenever entries change
            modified.append(rel(p))
        continue
    top = p                        # report only the topmost NEW entry
    while os.path.dirname(top) in changed and os.path.dirname(top) not in before:
        top = os.path.dirname(top)
    created.add(rel(top))
json.dump({"modified": modified, "created": sorted(created)}, open(sys.argv[3], "w"), indent=1)
PY
kill "$MOCK_PID" 2>/dev/null
exit 0
