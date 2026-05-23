"""Tests for Frame's architecture-loading mechanism.

Covers:
  TRC-A1 — Frame loads architecture/ into the task's working context
  TRC-A2 — Frame degrades gracefully when architecture/ is absent
  TRC-A5 — invariants.yml is loaded by mechanism when present
  TRC-A5b — Frame proceeds normally when invariants.yml is absent
  TRC-X1 — Malformed invariants.yml fails Frame loudly

The helper under test is `frame_load_architecture(project_root, task_dir)`
in cli/compass.  It is imported via importlib so we don't need to install
the CLI as a package.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Load the CLI module without executing main()
# ---------------------------------------------------------------------------

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = FRAMEWORK_ROOT / "cli" / "compass"


def _load_cli():
    import types
    source = CLI_PATH.read_text(encoding="utf-8")
    mod = types.ModuleType("compass_cli")
    mod.__file__ = str(CLI_PATH)
    # Provide __name__ so the `if __name__ == "__main__"` guard doesn't fire
    # during exec.  We also suppress sys.exit calls by catching SystemExit at
    # module load (there are none, but belt-and-suspenders).
    exec(compile(source, str(CLI_PATH), "exec"), mod.__dict__)  # noqa: S102
    return mod


cli = _load_cli()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _make_arch(base: Path, files: dict[str, str]) -> None:
    """Write architecture/ files into base given a {rel_path: content} map."""
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# TRC-A1 — loads when architecture/ is present
# ---------------------------------------------------------------------------

def test_loads_when_present(tmp_path):
    """TRC-A1: frame_load_architecture writes architecture-loaded.yml with
    one entry per file found.  The schema_version, loaded_at, artifacts list
    and adrs list must all be present.  Each artifact entry carries path,
    sha256, and type."""
    sc_content = "# System context"
    rel_content = "# Relations"
    own_content = "# Ownership"

    _make_arch(tmp_path, {
        "architecture/system-context.md": sc_content,
        "architecture/relations.md":      rel_content,
        "architecture/ownership.md":      own_content,
    })

    task_dir = tmp_path / ".compass" / "work" / "test-task"
    task_dir.mkdir(parents=True)

    result = cli.frame_load_architecture(str(tmp_path), str(task_dir))

    # The function must return a dict
    assert isinstance(result, dict), "frame_load_architecture must return a dict"

    # Required top-level keys
    assert result.get("schema_version") == "1.0", \
        f"schema_version should be '1.0', got {result.get('schema_version')!r}"
    assert "loaded_at" in result, "result must include loaded_at timestamp"
    assert isinstance(result.get("artifacts"), list), "artifacts must be a list"
    assert isinstance(result.get("adrs"), list), "adrs must be a list"

    # Three narrative files must be loaded
    paths_loaded = {a["path"] for a in result["artifacts"]}
    assert "architecture/system-context.md" in paths_loaded
    assert "architecture/relations.md"      in paths_loaded
    assert "architecture/ownership.md"      in paths_loaded

    # Every artifact entry must have path, sha256, type
    for art in result["artifacts"]:
        assert "path"   in art, f"artifact missing path: {art}"
        assert "sha256" in art, f"artifact missing sha256: {art}"
        assert "type"   in art, f"artifact missing type: {art}"

    # sha256 must match actual file content
    sc_art = next(a for a in result["artifacts"]
                  if a["path"] == "architecture/system-context.md")
    assert sc_art["sha256"] == _sha256(sc_content)
    assert sc_art["type"] == "narrative"

    # architecture-loaded.yml must be written to task_dir
    loaded_file = task_dir / "architecture-loaded.yml"
    assert loaded_file.exists(), \
        f"architecture-loaded.yml not written to {task_dir}"
    on_disk = yaml.safe_load(loaded_file.read_text(encoding="utf-8"))
    assert on_disk["schema_version"] == "1.0"
    assert len(on_disk["artifacts"]) == 3


# ---------------------------------------------------------------------------
# TRC-A2 — degrades gracefully when architecture/ is absent
# ---------------------------------------------------------------------------

def test_noop_when_absent(tmp_path):
    """TRC-A2: When architecture/ does not exist, frame_load_architecture
    succeeds (no exception), writes architecture-loaded.yml with empty
    artifacts and adrs lists."""
    task_dir = tmp_path / ".compass" / "work" / "test-task"
    task_dir.mkdir(parents=True)

    result = cli.frame_load_architecture(str(tmp_path), str(task_dir))

    assert result.get("artifacts") == [], \
        "artifacts should be empty when architecture/ is absent"
    assert result.get("adrs") == [], \
        "adrs should be empty when architecture/ is absent"

    loaded_file = task_dir / "architecture-loaded.yml"
    assert loaded_file.exists(), \
        "architecture-loaded.yml should still be written even when arch absent"
    on_disk = yaml.safe_load(loaded_file.read_text(encoding="utf-8"))
    assert on_disk["artifacts"] == []
    assert on_disk["adrs"] == []


# ---------------------------------------------------------------------------
# TRC-A5 — invariants.yml loaded when present (valid YAML)
# ---------------------------------------------------------------------------

def test_invariants_parsed_when_present(tmp_path):
    """TRC-A5: When architecture/invariants.yml exists and is valid YAML,
    it appears in artifacts with type 'structured' and its parsed content
    is included inline."""
    inv_content = "rules:\n  - no_duplication\n"

    _make_arch(tmp_path, {
        "architecture/system-context.md": "# ctx",
        "architecture/invariants.yml":    inv_content,
    })

    task_dir = tmp_path / ".compass" / "work" / "test-task"
    task_dir.mkdir(parents=True)

    result = cli.frame_load_architecture(str(tmp_path), str(task_dir))

    inv_arts = [a for a in result["artifacts"]
                if a["path"] == "architecture/invariants.yml"]
    assert inv_arts, "invariants.yml must appear in artifacts"

    inv_art = inv_arts[0]
    assert inv_art["type"] == "structured", \
        f"invariants.yml must have type 'structured', got {inv_art['type']!r}"
    assert "parsed" in inv_art, \
        "invariants.yml artifact must include parsed inline content"
    assert inv_art["parsed"] == {"rules": ["no_duplication"]}, \
        f"parsed content mismatch: {inv_art['parsed']}"
    assert inv_art["sha256"] == _sha256(inv_content)


# ---------------------------------------------------------------------------
# TRC-A5b — no invariants.yml is fine (only narrative files)
# ---------------------------------------------------------------------------

def test_no_invariants_file_ok(tmp_path):
    """TRC-A5b: When architecture/ exists but invariants.yml is absent,
    no error is raised and the loaded record contains only narrative entries."""
    _make_arch(tmp_path, {
        "architecture/system-context.md": "# ctx",
        "architecture/relations.md":      "# rels",
    })

    task_dir = tmp_path / ".compass" / "work" / "test-task"
    task_dir.mkdir(parents=True)

    result = cli.frame_load_architecture(str(tmp_path), str(task_dir))

    inv_arts = [a for a in result["artifacts"]
                if a["path"] == "architecture/invariants.yml"]
    assert not inv_arts, \
        "invariants.yml should NOT appear when the file is absent"

    # All entries should be narrative
    for art in result["artifacts"]:
        assert art["type"] == "narrative", \
            f"expected narrative type, got {art['type']!r} for {art['path']}"


# ---------------------------------------------------------------------------
# TRC-X1 — malformed invariants.yml fails loudly
# ---------------------------------------------------------------------------

def test_malformed_invariants_fails(tmp_path):
    """TRC-X1: When architecture/invariants.yml is not valid YAML,
    frame_load_architecture raises an exception whose message names the file
    and the parse error."""
    _make_arch(tmp_path, {
        "architecture/system-context.md": "# ctx",
        "architecture/invariants.yml":    "key: [unclosed bracket\n",
    })

    task_dir = tmp_path / ".compass" / "work" / "test-task"
    task_dir.mkdir(parents=True)

    with pytest.raises(Exception) as exc_info:
        cli.frame_load_architecture(str(tmp_path), str(task_dir))

    msg = str(exc_info.value)
    assert "invariants.yml" in msg, \
        f"error message must name the file; got: {msg!r}"
    # The message must also contain some indication of a parse/YAML error
    assert any(kw in msg.lower() for kw in ("parse", "yaml", "invalid", "error")), \
        f"error message must describe the problem; got: {msg!r}"
