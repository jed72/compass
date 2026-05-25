"""
Tests for TRC-B4, TRC-B5, TRC-B8 — verify.fitness route promotion and
architecture documentation.

Stream-B builder — farley-guidebook task.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import yaml

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = FRAMEWORK_ROOT / "cli" / "compass"


def _run_cli(*args: str, cwd: Path,
             extra_env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def _setup_gov(tmp_path: Path) -> Path:
    """Copy shipped governance into tmp_path."""
    import shutil
    gov_src = FRAMEWORK_ROOT / "governance"
    gov_dst = tmp_path / "governance"
    gov_dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(gov_src / "routing-policy.yml", gov_dst / "routing-policy.yml")
    shutil.copyfile(gov_src / "guardrails.yml", gov_dst / "guardrails.yml")
    (tmp_path / ".compass").mkdir(exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# TRC-B4: verify.fitness promoted when blast_radius is cross-cutting or critical
# ---------------------------------------------------------------------------

class TestVerifyFitnessPromotionBlastRadius:
    """TRC-B4: verify.fitness is promoted to blocking when blast_radius reaches
    cross-cutting or critical."""

    def test_cross_cutting_blast_radius_adds_verify_fitness(self, tmp_path):
        """route evaluate on blast_radius=cross-cutting includes verify.fitness
        in the gate set."""
        project_root = _setup_gov(tmp_path)
        result = _run_cli(
            "route", "evaluate", "--json",
            "--reading", "blast_radius=cross-cutting",
            "--reading", "terrain=brownfield-mapped",
            "--reading", "magnitude=standard",
            "--reading", "intent=delivery",
            cwd=project_root,
        )
        assert result.returncode == 0, (
            f"route evaluate failed: {result.stderr}"
        )
        data = json.loads(result.stdout)
        assert "verify.fitness" in data["gates"], (
            f"Expected verify.fitness in gates for cross-cutting blast_radius, "
            f"got: {data['gates']}"
        )

    def test_critical_blast_radius_adds_verify_fitness(self, tmp_path):
        """route evaluate on blast_radius=critical includes verify.fitness."""
        project_root = _setup_gov(tmp_path)
        result = _run_cli(
            "route", "evaluate", "--json",
            "--reading", "blast_radius=critical",
            "--reading", "terrain=brownfield-mapped",
            "--reading", "magnitude=large",
            "--reading", "intent=delivery",
            cwd=project_root,
        )
        assert result.returncode == 0, f"route evaluate failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert "verify.fitness" in data["gates"]

    def test_fired_guardrails_names_floor_rg_floor_006(self, tmp_path):
        """When cross-cutting fires RG-FLOOR-006, it appears in fired_guardrails."""
        project_root = _setup_gov(tmp_path)
        result = _run_cli(
            "route", "evaluate", "--json",
            "--reading", "blast_radius=cross-cutting",
            "--reading", "terrain=brownfield-mapped",
            "--reading", "magnitude=standard",
            "--reading", "intent=delivery",
            cwd=project_root,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        floor_ids = [f["id"] for f in data.get("fired_guardrails", [])]
        assert "RG-FLOOR-006" in floor_ids, (
            f"Expected RG-FLOOR-006 in fired_guardrails, got: {floor_ids}"
        )

    def test_contained_blast_radius_does_not_add_verify_fitness(self, tmp_path):
        """blast_radius=contained does NOT promote verify.fitness."""
        project_root = _setup_gov(tmp_path)
        result = _run_cli(
            "route", "evaluate", "--json",
            "--reading", "blast_radius=contained",
            "--reading", "terrain=brownfield-mapped",
            "--reading", "magnitude=small",
            "--reading", "intent=delivery",
            cwd=project_root,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "verify.fitness" not in data["gates"], (
            f"verify.fitness should NOT be in gates for contained, "
            f"got: {data['gates']}"
        )


# ---------------------------------------------------------------------------
# TRC-B5: verify.fitness promoted when touches includes an irreversible domain
# ---------------------------------------------------------------------------

class TestVerifyFitnessPromotionTouches:
    """TRC-B5: verify.fitness is promoted to blocking when touches lists an
    irreversible domain."""

    @pytest.mark.parametrize("domain", ["auth", "payments", "personal-data", "migrations"])
    def test_irreversible_domain_adds_verify_fitness(self, tmp_path, domain):
        """touches: [<domain>] causes verify.fitness to be added to gate set."""
        project_root = _setup_gov(tmp_path)
        result = _run_cli(
            "route", "evaluate", "--json",
            "--reading", "blast_radius=contained",
            "--reading", "terrain=brownfield-mapped",
            "--reading", "magnitude=small",
            "--reading", "intent=delivery",
            "--reading", f"touches={domain}",
            cwd=project_root,
        )
        assert result.returncode == 0, (
            f"route evaluate failed for domain={domain}: {result.stderr}"
        )
        data = json.loads(result.stdout)
        assert "verify.fitness" in data["gates"], (
            f"Expected verify.fitness for touches=[{domain}], "
            f"got gates: {data['gates']}"
        )

    def test_fired_guardrails_names_floor_rg_floor_007(self, tmp_path):
        """When touches fires RG-FLOOR-007, it appears in fired_guardrails."""
        project_root = _setup_gov(tmp_path)
        result = _run_cli(
            "route", "evaluate", "--json",
            "--reading", "blast_radius=contained",
            "--reading", "terrain=brownfield-mapped",
            "--reading", "magnitude=small",
            "--reading", "intent=delivery",
            "--reading", "touches=auth",
            cwd=project_root,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        floor_ids = [f["id"] for f in data.get("fired_guardrails", [])]
        assert "RG-FLOOR-007" in floor_ids, (
            f"Expected RG-FLOOR-007 in fired_guardrails, got: {floor_ids}"
        )

    def test_safe_domain_does_not_add_verify_fitness(self, tmp_path):
        """A non-irreversible domain does not promote verify.fitness."""
        project_root = _setup_gov(tmp_path)
        result = _run_cli(
            "route", "evaluate", "--json",
            "--reading", "blast_radius=contained",
            "--reading", "terrain=brownfield-mapped",
            "--reading", "magnitude=small",
            "--reading", "intent=delivery",
            "--reading", "touches=public-api",
            cwd=project_root,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "verify.fitness" not in data["gates"], (
            f"verify.fitness should NOT appear for touches=public-api, "
            f"got: {data['gates']}"
        )


# ---------------------------------------------------------------------------
# TRC-B8: architecture/ documents the fitness-functions pattern
# ---------------------------------------------------------------------------

class TestArchitectureDocumentation:
    """TRC-B8: architecture/ documents the fitness-functions pattern."""

    ARCH_DIR = FRAMEWORK_ROOT / "architecture"
    DECISIONS_DIR = FRAMEWORK_ROOT / "architecture" / "decisions"

    def test_adr_009_exists(self):
        """ADR-009 file must exist in architecture/decisions/."""
        adr_file = (
            self.DECISIONS_DIR
            / "ADR-009-fitness-functions-are-project-guardrails.md"
        )
        assert adr_file.is_file(), (
            f"ADR-009 not found at {adr_file}"
        )

    def test_adr_009_status_is_proposed(self):
        """ADR-009 must have status: proposed in its frontmatter."""
        adr_file = (
            self.DECISIONS_DIR
            / "ADR-009-fitness-functions-are-project-guardrails.md"
        )
        if not adr_file.is_file():
            pytest.skip("ADR-009 not yet created")
        text = adr_file.read_text(encoding="utf-8")
        assert "proposed" in text.lower(), (
            "ADR-009 must have status: proposed"
        )

    def test_adr_009_covers_command_passes_and_verify_fitness(self):
        """ADR-009 must mention command-passes and verify.fitness."""
        adr_file = (
            self.DECISIONS_DIR
            / "ADR-009-fitness-functions-are-project-guardrails.md"
        )
        if not adr_file.is_file():
            pytest.skip("ADR-009 not yet created")
        text = adr_file.read_text(encoding="utf-8")
        assert "command-passes" in text, "ADR-009 must mention command-passes"
        assert "verify.fitness" in text, "ADR-009 must mention verify.fitness"

    def test_adr_009_in_decisions_readme(self):
        """ADR-009 must be listed in architecture/decisions/README.md."""
        readme = self.DECISIONS_DIR / "README.md"
        assert readme.is_file()
        text = readme.read_text(encoding="utf-8")
        assert "ADR-009" in text, "ADR-009 must be indexed in decisions/README.md"

    def test_system_context_mentions_adr_009(self):
        """architecture/system-context.md must reference ADR-009."""
        sc = self.ARCH_DIR / "system-context.md"
        assert sc.is_file()
        text = sc.read_text(encoding="utf-8")
        assert "ADR-009" in text, (
            "system-context.md must contain a sentence pointing at ADR-009"
        )

    def test_evidence_gates_skill_mentions_fitness_functions(self):
        """skills/evidence-gates/SKILL.md must describe the fitness-functions
        pattern citing ADR-009."""
        skill = FRAMEWORK_ROOT / "skills" / "evidence-gates" / "SKILL.md"
        assert skill.is_file()
        text = skill.read_text(encoding="utf-8")
        assert "fitness" in text.lower(), (
            "evidence-gates SKILL.md must mention fitness functions"
        )
        assert "ADR-009" in text, (
            "evidence-gates SKILL.md must cite ADR-009"
        )
