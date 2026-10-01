# tests/

**Purpose:** Automated tests for the Python code in `src/`. Tests catch bugs early so that when new code is added, we know it didn't break something that was already working.

---

## Structure

```
tests/
├── test_parser.py           # Tests for src/parser/meson_parser.py and wrap_parser.py
├── test_placement.py        # Tests for src/placement/ (all three schemes + difficulty)
├── test_engine.py           # Tests for src/engine/mutant_generator.py and template_filler.py
├── fixtures/                # Small fake build files used as test inputs
│   ├── simple.meson.build   # A minimal meson.build with one dependency
│   ├── conditional.meson.build  # A meson.build with if/endif blocks
│   └── example.wrap         # A minimal .wrap file
└── conftest.py              # Shared test setup (pytest configuration)
```

---

## What Gets Tested

### `test_parser.py`
Checks that `meson_parser.py` correctly reads build files. For example:
- Given a `meson.build` file that declares `zlib` as a dependency, the parser should return a dependency entry for `zlib`.
- Given a `meson.build` with an `if host_machine.system() == 'windows'` block, the parser should return that conditional block.
- Given a `.wrap` file, the parser should return its `source_url` and `source_hash` fields.

### `test_placement.py`
Checks that the placement algorithms find the right injection sites. For example:
- Given a project with two `.wrap` files, `dependency_aware.py` should return both as candidates for URL-replacement attacks.
- Given a build file with a nested `if` block, `config_aware.py` should identify it as a candidate.
- `difficulty.py` should assign difficulty 1 to an injection in the main code path and difficulty 3 to an injection inside a conditional.

### `test_engine.py`
Checks that the engine produces valid, correctly-modified mutants. For example:
- Given a `.wrap` file and an `OP-001` operator, `mutant_generator.py` should produce a new `.wrap` file where the `source_url` field has changed.
- The output mutant should be valid Meson syntax (not broken or unparseable).
- The `mutant.json` metadata file should be written alongside the mutant.

---

## Running the Tests

```bash
# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_parser.py

# Run with verbose output (see each test's name and result)
pytest tests/ -v

# Run and stop at the first failure
pytest tests/ -x
```

You need `pytest` installed — it is listed in `src/requirements.txt`, so `pip install -r src/requirements.txt` covers it.

---

## How to Write a Test

Tests are regular Python functions that start with `test_`. Here is a minimal example:

```python
# tests/test_parser.py

from src.parser.wrap_parser import parse_wrap_file

def test_parse_url():
    """Parser should extract the source_url from a .wrap file."""
    result = parse_wrap_file("tests/fixtures/example.wrap")
    assert result["source_url"] == "https://example.com/zlib-1.3.tar.gz"

def test_parse_hash():
    """Parser should extract the source_hash from a .wrap file."""
    result = parse_wrap_file("tests/fixtures/example.wrap")
    assert "source_hash" in result
```

Each test function asserts something specific. If the assertion is wrong, pytest reports a failure.

---

## What Makes a Good Test

- **Small inputs:** Use the files in `fixtures/` (small, hand-written fake build files) rather than real target project files. Real files are large and slow.
- **One thing per test:** Each `test_` function should check exactly one behavior. If it fails, you know exactly what broke.
- **Descriptive names:** `test_parse_url` is better than `test1`. The name appears in the output when a test fails.
- **No side effects:** Tests should not modify `data/` or write files to disk. Use Python's `tmp_path` fixture if you need temporary file output.

---

## CI Integration

The `.github/workflows/ci.yml` file runs `pytest tests/` automatically on every push. If any test fails, the commit gets a red ✗ on GitHub. Keep the tests green.
