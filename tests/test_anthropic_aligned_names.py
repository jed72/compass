"""The command, agent and skill names renamed to match Anthropic's vocabulary.

ADR-023 records the rule. Eight filenames move under it. Each retired command
name was kept on disk as a redirect stub through 3.x under ADR-019, and all
of them were removed at 4.0.0 under ADR-024 - so a retired name is now an
unknown command, and `docs/releasing.md` is where a caller finds out what to
type instead.

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
# Retired command name -> replacement. The stub was removed at 4.0.0; the
# mapping stays so this file can still assert nothing points at the old name.
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
            # Derived at ship from the scenarios landed issues recorded, which
            # keep the names they landed under. Exempt from the vocabulary
            # scan for the same reason.
            if path.name == "system-spec.md":
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


# --- TRC-C1 / TRC-C2 - the command, and the absence of its stub -----------

def test_the_renamed_command_exists():
    """TRC-C1."""
    assert (COMMANDS / "consult.md").is_file()


def test_the_retired_command_name_no_longer_resolves():
    """TRC-C2: removed at 4.0.0, the boundary ADR-019 scheduled it for.

    This asserted the opposite through 3.x, when `roundtable.md` was a
    redirect stub. Inverted rather than deleted so something still objects if
    a stub reappears; ADR-024 records why the redirect was not carried on.
    """
    assert not (COMMANDS / "roundtable.md").is_file(), (
        "`/compass:roundtable` still ships. It was a redirect stub through "
        "3.x and was removed at 4.0.0")
    assert (COMMANDS / "consult.md").is_file(), (
        "the retired name is gone but `/compass:consult` does not exist, so "
        "the rename left a reader nowhere to go")


# --- TRC-C6 - the skills --------------------------------------------------

def test_the_renamed_skills_exist_under_their_new_names():
    """TRC-C6."""
    for old, new in RENAMED_SKILLS.items():
        assert (SKILLS / new / "SKILL.md").is_file(), f"{new} missing"
        assert not (SKILLS / old).exists(), f"{old} still present"


# --- TRC-C6 - nothing live still points at a retired name -----------------

def test_no_live_surface_points_at_a_retired_name():
    """A rename that leaves the cross-references behind is half a rename.

    Through 3.x the redirect stub was the one file allowed to name its own
    retired command. The stubs went at 4.0.0, so the only page that still
    needs to name one is `docs/releasing.md`, where the upgrade table tells a
    broken caller what to type instead - and it is excused for that name
    alone, not for the page.
    """
    retired = set(RENAMED_AGENTS) | set(RENAMED_SKILLS) | set(RENAMED_COMMANDS)
    # Per name where a name is what needs excusing. Exempting a whole page
    # excuses all eight retired identifiers when only one has a reason to be
    # there, and the page stops being guarded without anyone deciding that.
    # `glossary.md` is the one page excused for all eight, because it is
    # generated wholesale from the vocabulary and every banned word in it
    # arrived from its source.
    allowed = {
        # The upgrade table names the removed command beside its replacement,
        # because a reader whose script broke has to find their spelling here.
        REPO_ROOT / "docs" / "releasing.md": {"roundtable"},
        # Generated from governance/terminology.yml. Hand-editing a derived
        # page is how a derivation silently stops matching its source - the
        # terminology file records its drift guard catching exactly that - so
        # this page moves when its source does, not before.
        REPO_ROOT / "docs" / "glossary.md": set(retired),
    }
    hits = []
    for path in _live_files():
        excused = allowed.get(path, set())
        text = path.read_text(encoding="utf-8")
        for name in retired:
            if name in excused:
                continue
            if name in text:
                rel = path.relative_to(REPO_ROOT)
                hits.append(f"{rel}: {name}")
    assert not hits, "live surfaces still name retired identifiers:\n  " + \
        "\n  ".join(sorted(hits))
