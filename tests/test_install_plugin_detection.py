"""Acceptance tests for task fix-hook-double-fire.

Each test_trc_* function asserts the fix for one scenario in
.compass/work/fix-hook-double-fire/spec.feature.md. Tests shell out to
`scripts/install.sh` against a `tmp_path` directory pre-seeded for the case
and inspect exit code, stdout, and the resulting `.claude/settings.json`.

These tests are independent of `tests/conftest.py`'s `project` fixture
(which is shaped for the CLI's behaviour) — install.sh's behaviour is the
subject here, and a plain tmp directory is the right scaffold for it.
"""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSTALL_SH = ROOT / "scripts" / "install.sh"


def _run_install(target_dir, *extra_args, timeout=30):
    return subprocess.run(
        ["bash", str(INSTALL_SH), "--project", str(target_dir), *extra_args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=timeout,
        check=False,
    )


def _seed_plugin_manifest(target_dir):
    manifest_dir = target_dir / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "plugin.json").write_text(
        '{"name": "test-plugin", "version": "0.0.0"}\n'
    )


def _seed_existing_compass_hooks(target_dir):
    """Plant a settings.json that already contains all three Compass hook
    entries, as if `install.sh --project` had been run against this dir
    before the fix. Simulates the current bad state."""
    claude_dir = target_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    pre = {
        "hooks": {
            "PreToolUse": [{
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [{
                    "type": "command",
                    "command": str(ROOT / "hooks" / "pre-tool.sh"),
                }],
            }],
            "PostToolUse": [{
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [{
                    "type": "command",
                    "command": str(ROOT / "hooks" / "post-tool.sh"),
                }],
            }],
            "Stop": [{
                "hooks": [{
                    "type": "command",
                    "command": str(ROOT / "hooks" / "stop.sh"),
                }],
            }],
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(pre))


def _read_settings(target_dir):
    path = target_dir / ".claude" / "settings.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _compass_hook_paths(settings):
    """Hook commands in settings that point at this repo's hooks/ dir."""
    if not settings or "hooks" not in settings:
        return []
    found = []
    for event in ("PreToolUse", "PostToolUse", "Stop"):
        for entry in settings["hooks"].get(event, []):
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                if str(ROOT) in cmd and "/hooks/" in cmd:
                    found.append(cmd)
    return found


# ---------------------------------------------------------------------------
# Group A — install.sh refuses double-registration in a plugin-source target
# ---------------------------------------------------------------------------

def test_trc_a1_install_skips_hooks_in_plugin_source(tmp_path):
    """install.sh refuses hook registration when target has .claude-plugin/plugin.json."""
    _seed_plugin_manifest(tmp_path)

    result = _run_install(tmp_path)

    assert result.returncode == 0, (
        f"install.sh failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    settings = _read_settings(tmp_path)
    compass_hooks = _compass_hook_paths(settings)
    assert compass_hooks == [], (
        f"install.sh registered Compass hooks in a plugin-source target.\n"
        f"Found: {compass_hooks}\n"
        f"settings.json: {json.dumps(settings, indent=2) if settings else 'absent'}"
    )
    assert "plugin" in result.stdout.lower(), (
        f"install.sh did not explain that the target is a plugin source. "
        f"stdout:\n{result.stdout}"
    )


def test_trc_a2_install_cleans_existing_duplicate_on_rerun(tmp_path):
    """install.sh removes prior Compass hooks when re-run inside a plugin-source target."""
    _seed_plugin_manifest(tmp_path)
    _seed_existing_compass_hooks(tmp_path)

    # Sanity: the pre-seed put three compass hooks in place.
    assert len(_compass_hook_paths(_read_settings(tmp_path))) == 3, (
        "test setup failed — pre-seed should leave 3 Compass hooks in settings"
    )

    result = _run_install(tmp_path)

    assert result.returncode == 0, (
        f"install.sh failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    settings = _read_settings(tmp_path)
    compass_hooks = _compass_hook_paths(settings)
    assert compass_hooks == [], (
        f"install.sh did not strip prior Compass hook entries from a "
        f"plugin-source target.\nRemaining: {compass_hooks}"
    )


# ---------------------------------------------------------------------------
# Group B — non-plugin install regression guard
# ---------------------------------------------------------------------------

def test_trc_b1_install_registers_hooks_in_non_plugin_target(tmp_path):
    """install.sh registers hooks normally when target has no plugin manifest."""
    # tmp_path has no .claude-plugin/plugin.json — the canonical install target.
    result = _run_install(tmp_path)

    assert result.returncode == 0, (
        f"install.sh failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    settings = _read_settings(tmp_path)
    compass_hooks = _compass_hook_paths(settings)
    assert len(compass_hooks) == 3, (
        f"install.sh did not register the three Compass hooks in a "
        f"non-plugin target. Found: {compass_hooks}\n"
        f"settings: {json.dumps(settings, indent=2) if settings else 'absent'}"
    )

    # Idempotency: a second run produces the same result.
    result2 = _run_install(tmp_path)
    assert result2.returncode == 0
    compass_hooks2 = _compass_hook_paths(_read_settings(tmp_path))
    assert len(compass_hooks2) == 3, (
        f"Second run produced {len(compass_hooks2)} hooks (expected 3)"
    )


# ---------------------------------------------------------------------------
# Group C — --uninstall recovery
# ---------------------------------------------------------------------------

def test_trc_c1_uninstall_strips_hooks_regardless_of_plugin(tmp_path):
    """--uninstall removes Compass hooks even when a plugin manifest is present."""
    _seed_plugin_manifest(tmp_path)
    _seed_existing_compass_hooks(tmp_path)

    result = _run_install(tmp_path, "--uninstall")

    assert result.returncode == 0, (
        f"install.sh --uninstall failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    compass_hooks = _compass_hook_paths(_read_settings(tmp_path))
    assert compass_hooks == [], (
        f"--uninstall did not remove Compass hooks. Remaining: {compass_hooks}"
    )

    # The plugin manifest is untouched.
    assert (tmp_path / ".claude-plugin" / "plugin.json").exists(), (
        "--uninstall touched the plugin manifest — it must not"
    )

    # Idempotent.
    result2 = _run_install(tmp_path, "--uninstall")
    assert result2.returncode == 0


# ---------------------------------------------------------------------------
# Failure-mode coverage — detection precision
# ---------------------------------------------------------------------------

def test_trc_f1_detection_requires_actual_manifest_file(tmp_path):
    """Detection requires plugin.json — a directory without it is not a plugin source."""
    # A .claude-plugin/ dir exists but contains NO plugin.json.
    (tmp_path / ".claude-plugin").mkdir(parents=True, exist_ok=True)

    result = _run_install(tmp_path)

    assert result.returncode == 0, (
        f"install.sh failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    compass_hooks = _compass_hook_paths(_read_settings(tmp_path))
    assert len(compass_hooks) == 3, (
        f"install.sh treated a directory without plugin.json as a plugin "
        f"source. Found: {compass_hooks}"
    )
