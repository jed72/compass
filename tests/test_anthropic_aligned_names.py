"""The command, agent and skill names renamed to match Anthropic's vocabulary.

ADR-023 records the rule. Eight filenames move under it, and every retired
command name stays on disk as a redirect stub for one major version
(ADR-019), so an adopter's muscle memory gets a pointer rather than an
unknown-command error.

| Was | Is | Why |
|---|---|---|
| `agents/navigator.md` | `agents/router.md` | their "Routing" workflow pattern, and it runs routing-policy.yml |
| `agents/product-lens.md` | `agents/product-owner.md` | named for the role, which governance already lists |
| `agents/marketing-lens.md` | `agents/product-marketer.md` | same |
| `agents/architect-lens.md` | `agents/architect.md` | same |
| `commands/roundtable.md` | `commands/consult.md` | an advisor is "consulted mid-turn" |
| `skills/intent-elicitation` | `skills/intent-interview` | their onboarding doc runs an "interview" |
| `skills/blueprint-distillation` | `skills/behaviour-mapping` | distillation means model distillation to this audience |
| `skills/worktree-swarm` | `skills/worktree-multiagent` | swarm is another vendor's framework name |

Scenario ids: .compass/work/anthropic-aligned-vocabulary/acceptance-criteria.md
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
AGENTS = REPO_ROOT / "agents"
COMMANDS = REPO_ROOT / "commands"
SKILLS = REPO_ROOT / "skills"

RENAMED_AGENTS = {
    "navigator": "router",
    "product-lens": "product-owner",
    "marketing-lens": "product-marketer",
    "architect-lens": "architect",
}
RENAMED_SKILLS = {
    "intent-elicitation": "intent-interview",
    "blueprint-distillation": "behaviour-mapping",
    "worktree-swarm": "worktree-multiagent",
}
# Retired command name -> replacement. The stub stays for one major version.
RENAMED_COMMANDS = {"roundtable": "consult"}

# Everything a live instruction surface could point at a retired name from.
INSTRUCTION_SURFACES = ("agents", "commands", "skills", "approaches", "docs")


def _live_files():
    for rel in INSTRUCTION_SURFACES:
        root = REPO_ROOT / rel
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            # docs/analysis/ and docs/proposals/ are gitignored working notes,
            # not shipped surfaces - they are allowed to quote the old names.
            if "analysis" in path.parts or "proposals" in path.parts:
                continue
            yield path
    for name in ("README.md", "CLAUDE.md", "AGENTS.md"):
        path = REPO_ROOT / name
        if path.is_file():
            yield path


# --- TRC-C5 / TRC-C3 - the agents -----------------------------------------

def test_the_routing_agent_is_named_router():
    """TRC-C5: the agent that runs routing-policy.yml is called router."""
    assert (AGENTS / "router.md").is_file()
    assert not (AGENTS / "navigator.md").exists()


def test_the_role_agents_are_named_after_their_role():
    """TRC-C3: no agent filename ends in -lens; each names a governance role."""
    names = {p.stem for p in AGENTS.glob("*.md")}
    assert {"product-owner", "product-marketer", "architect"} <= names
    assert not [n for n in names if n.endswith("-lens")]


def test_no_agent_file_keeps_a_retired_name():
    for old in RENAMED_AGENTS:
        assert not (AGENTS / f"{old}.md").exists(), f"{old}.md still present"


# --- TRC-C1 / TRC-C2 - the command and its stub ---------------------------

def test_the_renamed_command_exists():
    """TRC-C1."""
    assert (COMMANDS / "consult.md").is_file()


def test_the_retired_command_name_still_resolves():
    """TRC-C2: a stub, not a deletion (ADR-019)."""
    stub = COMMANDS / "roundtable.md"
    assert stub.is_file(), "the retired name was deleted rather than stubbed"
    body = stub.read_text(encoding="utf-8")
    assert "/compass:consult" in body, "the stub does not name its replacement"
    assert "major version" in body, "the stub does not say how long it lasts"


# --- TRC-C6 - the skills --------------------------------------------------

def test_the_renamed_skills_exist_under_their_new_names():
    """TRC-C6."""
    for old, new in RENAMED_SKILLS.items():
        assert (SKILLS / new / "SKILL.md").is_file(), f"{new} missing"
        assert not (SKILLS / old).exists(), f"{old} still present"


# --- TRC-C6 - nothing live still points at a retired name -----------------

def test_no_live_surface_points_at_a_retired_name():
    """A rename that leaves the cross-references behind is half a rename.

    The stub is the one file allowed to name its own retired command, because
    naming it is the whole job.
    """
    retired = set(RENAMED_AGENTS) | set(RENAMED_SKILLS) | set(RENAMED_COMMANDS)
    allowed = {
        # Naming its own retired command is the stub's whole job.
        COMMANDS / "roundtable.md",
        # Generated from governance/terminology.yml. Hand-editing a derived
        # page is how a derivation silently stops matching its source - the
        # terminology file records its drift guard catching exactly that - so
        # this page moves when its source does, not before.
        REPO_ROOT / "docs" / "glossary.md",
    }
    hits = []
    for path in _live_files():
        if path in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        for name in retired:
            if name in text:
                rel = path.relative_to(REPO_ROOT)
                hits.append(f"{rel}: {name}")
    assert not hits, "live surfaces still name retired identifiers:\n  " + \
        "\n  ".join(sorted(hits))
