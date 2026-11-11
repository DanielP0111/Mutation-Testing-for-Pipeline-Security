#!/bin/bash
# One harness build step, run from /src. Used for every build (plain or under
# Foreman) so the steps, logs and exit codes are identical either way.
#
#   step.sh fetch|setup|compile|test
#
# Writes $OUT/<step>.log and $OUT/<step>.rc (-1 = skipped because an earlier
# step failed). Under Foreman each step is one build phase.
set -u
OUT=${OUT:-/work/out}   # the sandbox points this at a private dir
STEP="$1"
cd /src

rc_of() { cat "$OUT/$1.rc" 2>/dev/null || echo -1; }

case "$STEP" in
  fetch)
    meson subprojects download > "$OUT/fetch.log" 2>&1
    echo $? > "$OUT/fetch.rc"
    ;;
  setup)
    meson setup build --buildtype=release ${WRAP_MODE:+--wrap-mode=$WRAP_MODE} \
      > "$OUT/setup.log" 2>&1
    echo $? > "$OUT/setup.rc"
    ;;
  compile)
    if [ "$(rc_of setup)" != 0 ]; then echo -1 > "$OUT/compile.rc"; exit 0; fi
    # Generate custom-command headers first. Some targets under-declare them
    # (git v2.48.0: builtin/bugreport.c includes hook-list.h, which meson only
    # orders before libgit), so a parallel build races and fails at random.
    gen_headers=$(ninja -C build -t targets all 2>/dev/null \
      | awk -F': ' '$1 ~ /\.h$/ && $2 == "CUSTOM_COMMAND" {print $1}')
    {
      # shellcheck disable=SC2086
      { [ -z "$gen_headers" ] || ninja -C build $gen_headers; } &&
        meson compile -C build
    } > "$OUT/compile.log" 2>&1
    echo $? > "$OUT/compile.rc"
    ;;
  test)
    if [ "$(rc_of compile)" != 0 ]; then echo -1 > "$OUT/test.rc"; exit 0; fi
    find build -type f \( -name 'git' -o -name '*.a' -o -name '*.so' \) \
      -exec sha256sum {} + | sort -k2 > "$OUT/hashes.txt"
    if [ -n "${TESTS:-}" ]; then
      # shellcheck disable=SC2086
      meson test -C build $TESTS > "$OUT/tests.log" 2>&1
      echo $? > "$OUT/test.rc"
      cp build/meson-logs/testlog.json "$OUT/testlog.json" 2>/dev/null || true
    else
      echo -1 > "$OUT/test.rc"
    fi
    ;;
  *)
    echo "unknown step: $STEP" >&2; exit 2 ;;
esac
exit 0
