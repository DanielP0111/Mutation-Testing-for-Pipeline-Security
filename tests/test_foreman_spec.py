from pathlib import Path

from src.engine import foreman_spec as fs


def test_learn_restricts_untouched_top_level_entries(tmp_path: Path):
    for d in ("src", "t", "docs"):
        (tmp_path / d).mkdir()
    (tmp_path / "meson.build").write_text("x")
    info = tmp_path / "info.txt"
    info.write_text(
        "setup accessed /src/meson.build\n"
        "setup accessed /src/t\n"            # directory: ignored (Foreman's own scan)
        "compile accessed /src/src/a.c\n"
        "compile created /src/build/a.o\n"
    )
    spec = fs.learn_from_info(info, tmp_path)
    compile_r = spec["phases"]["compile"]["file"]["restricted"]
    assert "/src/t/" in compile_r and "/src/docs/" in compile_r
    assert "/src/src/" not in compile_r
    assert "/src/t/" in spec["phases"]["setup"]["file"]["restricted"]


def test_build_phases_use_harness_steps():
    phases = fs.to_build_phases({"phases": {"compile": {"file": {"restricted": ["/src/t/"]}}}})
    assert [p["name"] for p in phases] == ["fetch", "setup", "compile", "test"]
    assert phases[2]["commands"] == [["bash", "/work/harness/step.sh", "compile"]]
    assert phases[2]["permissions"]["file"]["restricted"] == ["/src/t/"]
    assert "permissions" not in phases[0]
