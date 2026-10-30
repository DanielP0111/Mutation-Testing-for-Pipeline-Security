# Foreman (vendored, unmodified)

- Source: artifact for Pappas & Gazzillo, "Build Code is Still Code: Finding the
  Antidote for Pipeline Poisoning", ICSE-NIER '26 (doi:10.1145/3786582.3786799).
- Zenodo: https://doi.org/10.5281/zenodo.18233614 (record), README cites 10.5281/zenodo.18190621.
- Downloaded 2026-10-30 as artifact.zip, md5 9ad37767e551ff84ae4f00d08cd04ed3
  (Zenodo lists v1.0.1 = 835eefb0…; this download is the newer version on the record).
- License: Apache-2.0 for the code (LICENSE, shipped in the artifact); the Zenodo record itself is CC BY 4.0.
- `foreman.py`, `README.md`, `LICENSE`, `demo.def`, `run-demo.sh` are copied
  verbatim. The demo XZ tarball (the real backdoored xz 5.6.0 source) is left
  inside artifact.zip on purpose and is not extracted.
- We do not edit foreman.py. `harness/foreman_launch.py` imports it and adds two
  shims, see that file:
  1. `os.reload_environ` exists only on Python 3.14; the harness image has 3.11.
     Foreman's env-var tracking re-reads its own process environment, which
     child processes cannot change, so a no-op shim does not change results.
  2. `is_file_in_any_paths` raises FileNotFoundError for a file deleted during
     a phase; the shim falls back to an equivalent path-prefix check.
