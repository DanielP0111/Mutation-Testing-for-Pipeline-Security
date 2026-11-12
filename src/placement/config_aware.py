"""
src/placement/config_aware.py

Finds injection candidates inside conditional blocks in meson.build files.

Strategy: configuration-aware placements target the conditional logic of
the build — if/elif blocks that gate platform-specific behavior, optional
features, or fallback dependencies.

Owned by David.

STATUS (Phase 3): branch-reachability analysis is implemented below
(`analyze_branch_reachability`, `load_build_options_from_introspect`) and is
fully functional and tested — it finds every conditional in the project,
works out what gates it (a `get_option()` name, a `host_machine.system()`
platform check, or nothing recognized), and reports whether that branch is
reachable under a given build configuration, mirroring what
`meson introspect --buildoptions` would tell you about the live build.

`find_config_candidates()`, the function `placer_api.find_candidates()`
actually calls, intentionally still returns `[]`. That function is the
other half of this scheme: turning a reachable branch into a candidate
dict (`field` / `current_value` / `placeholder_map`) that the engine would
use to splice an attack payload into that branch of a real project. That
step is what's being held back — see docs/config_aware_status.md for the
full explanation and what the team needs to decide/do to move it forward.
"""

import re

# Matches a get_option('name') read anywhere inside a condition string.
_OPTION_RE = re.compile(r"""get_option\(\s*['"]([^'"]+)['"]\s*\)""")

# Matches the common platform-guard idiom: host_machine.system() == 'linux'
_HOST_SYSTEM_RE = re.compile(
    r"""host_machine\.system\(\)\s*==\s*['"]([^'"]+)['"]"""
)

# Values meson/get_option() treats as "off" for a boolean/feature option.
_FALSY_OPTION_VALUES = {"false", "disabled", "", "0", "no"}


def _extract_gating_options(condition: str) -> list[str]:
    """Return every get_option('x') name referenced in a condition string."""
    return _OPTION_RE.findall(condition)


def _extract_platform_guard(condition: str) -> str | None:
    """Return the platform name if condition is gated on host_machine.system(), else None."""
    m = _HOST_SYSTEM_RE.search(condition)
    return m.group(1) if m else None


def analyze_branch_reachability(
    parsed_project: dict, build_options: dict | None = None
) -> list[dict]:
    """
    Report-only branch-reachability analysis over every conditional the
    parser found. Does NOT produce placement candidates (see module
    docstring) — this is purely descriptive, for use in the difficulty
    scale and in the team's writeup.

    Args:
        parsed_project: dict from parse_project() (reads ["conditionals"]).
        build_options: flat {option_name: value} dict, as produced by
            `load_build_options_from_introspect()` from real
            `meson introspect --buildoptions` JSON, plus an optional
            "host_system" key for platform-guard resolution. Pass None (the
            default) to get a report of what WOULD need to be true for each
            branch, without resolving it against an actual configuration.

    Returns:
        One dict per conditional block, in the order the parser found them:
        {
            "file_path": str,
            "line_start": int,
            "line_end": int | None,
            "condition": str,
            "depth": int,
            "gating_options": list[str],   # get_option() names in the condition
            "platform_guard": str | None,  # e.g. "linux", "windows", or None
            "reachable": bool | None,      # None = unresolved (no info supplied)
            "reachability_basis": str,     # human-readable explanation
        }
    """
    build_options = build_options or {}
    report = []

    for cond in parsed_project.get("conditionals", []):
        condition = cond.get("condition", "")
        gating_options = _extract_gating_options(condition)
        platform_guard = _extract_platform_guard(condition)

        reachable = None
        basis_parts = []

        if platform_guard:
            basis_parts.append(f"gated on host_machine.system() == '{platform_guard}'")
            host_hint = build_options.get("host_system")
            if host_hint is not None:
                reachable = host_hint == platform_guard
                basis_parts.append(f"build host_system={host_hint!r}")
            else:
                basis_parts.append("no host_system supplied — unresolved")

        if gating_options:
            basis_parts.append(f"gated on build option(s) {gating_options}")
            known = {name: build_options.get(name) for name in gating_options}
            if all(v is not None for v in known.values()):
                # Heuristic conjunction: every referenced option must be
                # truthy for a plain `if get_option(...)` branch to be
                # taken. This does not parse 'and' / 'or' / 'not' inside
                # `condition` — a compound boolean expression is reported
                # as gated on all the options it mentions, which is a
                # conservative over-approximation, not a real evaluator.
                opt_reachable = all(
                    bool(v) and str(v).lower() not in _FALSY_OPTION_VALUES
                    for v in known.values()
                )
                reachable = opt_reachable if reachable is None else (reachable and opt_reachable)
                basis_parts.append(f"current values {known}")
            else:
                basis_parts.append("build option values not supplied — unresolved")

        if not platform_guard and not gating_options:
            # No recognized gate (e.g. a condition on a variable computed
            # earlier, or on a dependency().found() result). We don't try
            # to evaluate arbitrary expressions — report it as reachable
            # by default, since nothing here rules it out.
            reachable = True if reachable is None else reachable
            basis_parts.append("no recognized option/platform gate found — treated as reachable")

        report.append(
            {
                "file_path": cond.get("file_path"),
                "line_start": cond.get("line_start"),
                "line_end": cond.get("line_end"),
                "condition": condition,
                "depth": cond.get("depth", 1),
                "gating_options": gating_options,
                "platform_guard": platform_guard,
                "reachable": reachable,
                "reachability_basis": "; ".join(basis_parts) if basis_parts else "no gate detected",
            }
        )

    return report


def load_build_options_from_introspect(introspect_json) -> dict:
    """
    Convert the JSON parsed from `meson introspect --buildoptions <builddir>`
    into the flat {option_name: value} shape `analyze_branch_reachability`
    expects as `build_options`.

    `meson introspect --buildoptions` has no notion of
    `host_machine.system()` — it's a cross-file/native concept, not a
    buildoption — so platform-guard resolution needs a separate hint. A
    caller that wants it resolved adds it after calling this function:

        opts = load_build_options_from_introspect(json.loads(output))
        opts["host_system"] = platform.system().lower()  # or a cross-file's value

    Args:
        introspect_json: the parsed JSON (a list of option dicts, each with
            at least "name" and "value" — the real `meson introspect
            --buildoptions` output shape).

    Returns:
        {option_name: value} flat dict. {} for anything not shaped like a
        list of option dicts.
    """
    flat = {}
    if isinstance(introspect_json, list):
        for entry in introspect_json:
            if isinstance(entry, dict) and entry.get("name"):
                flat[entry["name"]] = entry.get("value")
    return flat


def find_config_candidates(parsed_project: dict, operator: dict) -> list[dict]:
    """
    Find candidates using the configuration-aware placement strategy.

    This is the entry point `placer_api.find_candidates()` calls for the
    `config_aware` scheme. It intentionally returns `[]` — see the module
    docstring and docs/config_aware_status.md. The reachability analysis
    this scheme is built on is implemented above and is real and tested;
    what's not implemented is turning a reachable branch into a candidate
    dict the engine would use to write an attack payload into it.

    Each returned candidate must include:
        scheme, file_path, field, current_value, placeholder_map
    (difficulty is assigned later by difficulty.py)

    Returns [] if no candidates apply.
    """
    if operator.get("scheme") not in ("config_aware", "all"):
        return []
    return []
