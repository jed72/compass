"""Cross-cutting invariants for compass analyze + living-spec + compass next.

These tests are structural assertions that protect Compass's USPs across the
three capabilities introduced in the 1.0 line: legibility budget,
determinism boundary, refused-idea boundaries (no tier menu, no persona zoo,
no fixed-depth pipeline, no fluid no-gate mode, no mandatory universal TDD),
and zero-setup on-ramp.
"""

# The vocabulary rename landed on 2026-08-25: the assess and plan stages took
# the names their machine keys, skills and agents already used; `design` went
# back to the designer; design.md became technical-design.md and prd.md became
# intent.md. Spines and documents written before still load and resolve
# (ADR-006), so what moved is the CANONICAL spelling these tests assert - not
# what the framework computes. Re-pointed, not relaxed.
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
CLI = ROOT / "cli" / "compass"


# ---------------------------------------------------------------------------
# TRC-D1 - the five-point mental model gains zero new top-level concepts
# Source-of-truth: the bulleted list under
# "## The mental model in five points" in docs/five-minutes.md.
# ---------------------------------------------------------------------------
def test_trc_d1_mental_model_bullets_unchanged():
    """TRC-D1 - the bulleted list under "## The mental model in five points"
    in docs/five-minutes.md has the same number of top-level bullets it had
    before this task landed.

    The pre-task count is the five-point model - by design (the heading
    promises "five points"). The three candidates introduce zero net-new
    top-level concepts; the new CLI verbs (analyze, next) and the derived
    artifact (docs/system-spec.md) are products of existing concepts.
    """
    five_minutes = (ROOT / "docs" / "five-minutes.md").read_text(encoding="utf-8")
    # Find the section by heading
    m = re.search(
        r"^## The mental model in five points\s*$(.*?)^## ",
        five_minutes,
        re.MULTILINE | re.DOTALL,
    )
    assert m, "docs/five-minutes.md must contain '## The mental model in five points'"
    section = m.group(1)
    # Count top-level numbered items - lines starting with "1. ", "2. ", etc.
    # at column 0. The list in this section is numbered, not bulleted.
    top_level_items = re.findall(r"^\d+\.\s+", section, re.MULTILINE)
    assert len(top_level_items) == 5, (
        f"the five-point model must keep five top-level items; "
        f"found {len(top_level_items)}"
    )


# ---------------------------------------------------------------------------
# Public CLI surface guard. Originally TRC-D2 (cross-task-architectural-
# integrity) froze the surface at "+analyze, +next". It is now the framework's
# living public-surface fitness function: the public subcommand set must equal
# the known list below, so no verb is added (or a private one exposed) without
# a deliberate update here. framework-field-feedback (R5/R9) adds land-commit
# and the task-spine mutators; each addition updates this set on purpose.
# Leading-underscore subcommands stay private and excluded from --help (DD-4).
# ---------------------------------------------------------------------------
# The known set moved with the CLI-voice slice: the banned-word verbs
# renamed (route -> approach, task -> issue, backfill -> follow-up,
# calibration -> retro, plan -> design, land-commit -> ship-commit) and
# terminology was added. The assertion's premise is unchanged - the
# surface equals the known set, and deliberate changes update it here.
EXPECTED_PUBLIC_SUBCOMMANDS = {
    "approach", "check", "retro", "ci",
    "tdd-red", "tdd-green",
    "policy", "issue", "adr",
    "rework-scan", "flow", "follow-up",
    "terminology",                # the CLI-voice slice: the glossary verb
    "migrate",                    # slice 8: the 1.x-to-2.0 tree migrator
    "analyze", "next",            # cross-task-architectural-integrity
    "ship-commit",                # framework-field-feedback R5
    "gate", "scenario", "changed-file", "evidence",  # framework-field-feedback R6/R9
    "plan",                       # readable-specs-and-flow shipped this as
                                  # `compass design lint`, the advisory
                                  # placeholder scan over technical-design.md.
                                  # The vocabulary rename moved it to `plan` on
                                  # 2026-08-25, because `design` now names the
                                  # DESIGNER's stage and one word cannot mean
                                  # two stages in one release.
                                  # The retired spelling `design` still runs -
                                  # ADR-006 forbids breaking it mid-major - but
                                  # it is hidden from `--help`, so it is not an
                                  # advertised verb and is absent from this set.
    "acceptance",                 # honest-acceptance-for-config-and-refactor:
                                  # `compass acceptance start|record`, the
                                  # honest signal for a change with no natural
                                  # behavioural red (field report R13). A
                                  # GROUP, like `bdd`, so later kinds add
                                  # `compass acceptance <thing>`.
    "bdd",                        # executable-bdd-and-richer-plans:
                                  # `compass bdd extract`. A subcommand GROUP,
                                  # so later BDD work (a scenarios-are-executable
                                  # check) adds `compass bdd <thing>` rather than
                                  # another top-level verb.
}


def test_trc_d2_only_two_new_public_cli_verbs():
    """The public CLI surface equals the known set (no unexpected additions or
    removals), and `_derive-system-spec` stays hidden from `compass --help`
    (private entry point per DD-4). Deliberate additions update
    EXPECTED_PUBLIC_SUBCOMMANDS."""
    out = subprocess.run(
        [sys.executable, str(CLI), "--help"],
        check=True, capture_output=True, text=True,
    ).stdout
    # Parse the {a,b,c,...} positional argument listing in `compass --help`
    m = re.search(r"\{([a-z0-9_,\-]+)\}", out)
    assert m, "compass --help must list its subcommands in {a,b,...} form"
    actual = set(m.group(1).split(","))
    assert actual == EXPECTED_PUBLIC_SUBCOMMANDS, (
        f"public CLI surface drift: added {actual - EXPECTED_PUBLIC_SUBCOMMANDS}, "
        f"removed {EXPECTED_PUBLIC_SUBCOMMANDS - actual}. If deliberate, update "
        f"EXPECTED_PUBLIC_SUBCOMMANDS in this test."
    )
    # Private entry point must not appear in --help
    assert "_derive-system-spec" not in actual, (
        "_derive-system-spec is a private entry point and must not appear in compass --help"
    )


# ---------------------------------------------------------------------------
# TRC-D3 - no fixed-tier ladder is shipped
# Source-of-truth: governance/routing-policy.yml - no `tier`, `level`, or
# equivalent vocabulary; the four reading dimensions remain
# blast_radius/terrain/magnitude/intent (BR-012).
# ---------------------------------------------------------------------------
def test_trc_d3_no_tier_ladder_in_routing_policy():
    """TRC-D3 - governance/routing-policy.yml has no `tier` or `level`
    vocabulary; the four reading dimensions are unchanged."""
    text = (ROOT / "governance" / "routing-policy.yml").read_text(encoding="utf-8")
    # Hard prohibition - no "tier:" or "level:" keys anywhere
    for forbidden in ("tier:", "level:"):
        assert forbidden not in text, (
            f"routing-policy.yml must not introduce '{forbidden}' - would be a tier-ladder"
        )
    # Reading vocabulary keys are unchanged (the four dimensions + urgency + role)
    policy = yaml.safe_load(text)
    vocab = policy.get("assessment_vocabulary", {})
    expected_dims = {"risk", "familiarity", "size", "goal", "urgency", "role"}
    assert expected_dims.issubset(set(vocab.keys())), (
        f"assessment_vocabulary must contain {expected_dims}; got {set(vocab.keys())}"
    )


# ---------------------------------------------------------------------------
# TRC-D4 - the five roles remain lenses; no new agent persona was added
# Source-of-truth: agents/*.md and governance/routing-policy.yml's role
# enum. The agent count cannot grow, and the role enum stays at five.
# ---------------------------------------------------------------------------
PRE_TASK_AGENT_FILES = {
    "spec-author.md", "planner.md", "builder.md", "orchestrator.md",
    "verifier.md", "reviewer.md", "navigator.md",
    "product-lens.md", "marketing-lens.md", "architect-lens.md",
}
EXPECTED_ROLES = {
    "engineer", "product-owner", "product-marketer", "designer", "qa",
}


def test_trc_d4_no_new_agent_persona_no_new_role():
    """TRC-D4 - the count of role/lens agent files is unchanged; the five
    roles remain the canonical set (BR-013)."""
    agents_dir = ROOT / "agents"
    actual_agents = {p.name for p in agents_dir.glob("*.md")}
    # New agent files would be a BR-013 violation
    new_agents = actual_agents - PRE_TASK_AGENT_FILES
    assert not new_agents, (
        f"no new role/lens agent file may be added by this task; observed new: {new_agents}"
    )
    # Role enum unchanged
    policy = yaml.safe_load(
        (ROOT / "governance" / "routing-policy.yml").read_text(encoding="utf-8")
    )
    actual_roles = set(policy["assessment_vocabulary"]["role"])
    assert actual_roles == EXPECTED_ROLES, (
        f"the role enum must remain {EXPECTED_ROLES}; got {actual_roles}"
    )


# ---------------------------------------------------------------------------
# TRC-D5 - pipeline phases still flex by route
# Source-of-truth: governance/routing-policy.yml `route_shapes` - at least
# two route shapes differ in their phase-weight maps (BR-014).
# ---------------------------------------------------------------------------
def test_trc_d5_pipeline_phases_flex_by_route():
    """TRC-D5 - the five route shapes have different phase-weight maps;
    none has been flattened to a one-size-fits-all shape (BR-014)."""
    policy = yaml.safe_load(
        (ROOT / "governance" / "routing-policy.yml").read_text(encoding="utf-8")
    )
    shapes = policy["route_shapes"]
    phase_maps = {name: shape["stages"] for name, shape in shapes.items()}
    # All five shapes present
    assert {"spike", "express", "standard", "hotfix", "expedition"} == set(phase_maps.keys())
    # At least two shapes must have distinct phase maps
    distinct = {tuple(sorted(pm.items())) for pm in phase_maps.values()}
    assert len(distinct) >= 2, (
        "at least two route shapes must have different phase-weight maps; "
        f"all shapes resolved to {len(distinct)} unique phase map(s)"
    )
    # Specifically: a quick fix collapses the requirements review; a spike
    # skips the breakdown. Read by the CURRENT stage keys - the policy
    # declared the retired ones until 2026-08-25, which is the whole reason
    # `shape_stages` had to canonicalise them for every caller.
    assert phase_maps["express"]["refine"] in {"collapsed", "light"}
    assert phase_maps["spike"]["breakdown"] in {"skipped", "collapsed"}


# ---------------------------------------------------------------------------
# TRC-D6 - phases and gates remain enforced
# Source-of-truth: governance/routing-policy.yml `immovable_gates` and every
# route_shape's `gates` list (BR-015).
# ---------------------------------------------------------------------------
IMMOVABLE_GATE_IDS = {"verify.correctness", "verify.governance", "verify.traceability"}


def test_trc_d6_phases_and_gates_remain_enforced():
    """TRC-D6 - immovable gates are still immovable; no route shape's gate
    set is empty (no fluid no-gate mode, BR-015)."""
    policy = yaml.safe_load(
        (ROOT / "governance" / "routing-policy.yml").read_text(encoding="utf-8")
    )
    # Immovable gates present
    immovable = {g["gate"] for g in policy["routing_guardrails"]["immovable_gates"]}
    assert IMMOVABLE_GATE_IDS.issubset(immovable), (
        f"immovable gates must include {IMMOVABLE_GATE_IDS}; got {immovable}"
    )
    # No route shape has an empty gate set
    for name, shape in policy["route_shapes"].items():
        gates = shape.get("gates", [])
        assert gates, f"route shape '{name}' must not have an empty gate set"


# ---------------------------------------------------------------------------
# TRC-D7 - TDD remains a strategy that Spike suspends
# Source-of-truth: hooks/pre-tool.sh - must read a .spike marker and suspend
# enforcement on a Spike route (BR-016).
# ---------------------------------------------------------------------------
def test_trc_d7_tdd_remains_a_strategy_spike_suspends():
    """TRC-D7 - the pre-tool hook still reads the .spike marker and
    suspends red-before-green on Spike routes (BR-016)."""
    hook = (ROOT / "hooks" / "pre-tool.sh").read_text(encoding="utf-8")
    assert ".spike" in hook, "pre-tool.sh must read the .spike marker to be route-aware"
    # The hook still enforces .red elsewhere - sanity that it's not been removed
    assert ".red" in hook, "pre-tool.sh must still enforce the .red marker contract"


# ---------------------------------------------------------------------------
# TRC-D8 - every new capability functions on a bare repo with no /compass:init
# Source-of-truth: the CLI's behaviour when invoked from a bare directory
# with no project-level governance/ overrides. Falls back to the framework's
# shipped defaults (BR-004 / NFR-ONR-001).
# ---------------------------------------------------------------------------
def test_trc_d8_bare_repo_zero_setup(tmp_path):
    """TRC-D8 - `compass analyze` and `compass next` both produce a clean
    no-op behaviour when invoked from a bare repo without /compass:init."""
    # Bare repo - just a directory, no .compass/ at all
    out_analyze = subprocess.run(
        [sys.executable, str(CLI), "analyze"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    # On a bare repo, analyze should not crash with a parse error; it should
    # report cleanly that there are no artifacts. Exit code may be non-zero
    # because no task is framed - but the error must be informative, not a
    # traceback.
    assert "Traceback" not in out_analyze.stderr, (
        f"analyze on bare repo crashed: {out_analyze.stderr}"
    )
    out_next = subprocess.run(
        [sys.executable, str(CLI), "next"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert "Traceback" not in out_next.stderr, (
        f"next on bare repo crashed: {out_next.stderr}"
    )


# ---------------------------------------------------------------------------
# TRC-D9 - route composition stays byte-identical across runs
# Source-of-truth: `compass approach evaluate --json` for a fixed reading set
# returns byte-identical output across runs (NFR-DET-001).
# ---------------------------------------------------------------------------
def test_trc_d9_route_evaluate_deterministic(tmp_path):
    """TRC-D9 - `compass approach evaluate` is byte-identical for the same
    readings + the same routing policy."""
    # Run route evaluate twice with the same readings against the framework's
    # own routing-policy.yml (no project overrides - work in tmp_path).
    cmd = [
        sys.executable, str(CLI), "approach", "evaluate",
        "--assessment", "risk=contained",
        "--assessment", "familiarity=brownfield-mapped",
        "--assessment", "size=small",
        "--assessment", "intent=delivery",
        "--assessment", "role=engineer",
        "--json",
    ]
    out1 = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
    out2 = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
    # The route + phases + gates blocks must match byte-for-byte
    j1 = json.loads(out1.stdout)
    j2 = json.loads(out2.stdout)
    assert j1.get("delivery_approach") == j2.get("delivery_approach")
    assert j1.get("stages") == j2.get("stages")
    assert j1.get("gates") == j2.get("gates")


# ---------------------------------------------------------------------------
# TRC-D10 - the determinism boundary holds - no model call after readings
# Source-of-truth: static check of cli/compass for LLM SDK imports
# (BR-002 / NFR-DET-002).
# ---------------------------------------------------------------------------
FORBIDDEN_LLM_IMPORTS = (
    "import anthropic",
    "from anthropic",
    "import openai",
    "from openai",
    "import litellm",
    "from litellm",
    "import langchain",
    "from langchain",
)


def test_trc_d10_no_llm_sdk_in_cli():
    """TRC-D10 - `cli/compass` imports no LLM SDK on any code path. The
    determinism boundary is post-readings; the CLI is the post-boundary
    half and must be mechanism, not judgement."""
    cli_src = CLI.read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_LLM_IMPORTS:
        assert forbidden not in cli_src, (
            f"cli/compass must not import an LLM SDK; found '{forbidden}'"
        )
