# Compass CLI test suite

These tests defend the 1.0 safety contract (`docs/safety-contract.md`). They
shell out to the `compass` CLI in a temp project per test - no shared state,
no network calls.

## Run

The canonical command (from the repo root) is:

```bash
make test
```

which expands to:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -q
```

PyYAML, the CLI's one runtime dependency, travels inside the plugin
(`cli/vendor/yaml/`) and `tests/conftest.py` resolves it the same way the CLI
does - nothing to install there. `pytest` and `jsonschema` are test tooling
and enable the suite to run (`pip install pytest jsonschema`). The suite
spawns one CLI subprocess per test; on a healthy machine it completes in a
few seconds. Each `run_cli` call has a 10-second timeout - long enough for a
real run, short enough that a genuinely hung subprocess fails fast rather
than compounding across 93 tests.

### If `make test` hangs

A v1 reviewer hit a hang on `tests/test_check_guardrails.py` in a slow
environment. The likely cause is pytest plugin autoload (e.g. `ddtrace`,
coverage plugins, instrumentation) which `make test` already disables via
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. If you see a hang anyway, try:

```bash
# 1. Confirm no plugin is loading
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest --version

# 2. Run a single file to isolate the hang
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_check_guardrails.py -v

# 3. Stop on the first failure (faster triage)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -x -v

# 4. Look for hung pytest/python subprocesses
ps aux | grep -E 'pytest|python.*compass' | grep -v grep
```

If a single file or test hangs reliably, please file an issue with the
output of `python3 -m pytest --version` and the platform; subprocess
launch overhead varies wildly between filesystems.

## What the suite covers

Each test file maps to a section of the safety contract:

| File | Contract guarantee |
|---|---|
| `test_route_selection.py` | 1 - deterministic routing; floors and caps fire as documented |
| `test_spike_conflict.py`  | 4 - exploration cannot silently become delivery |
| `test_policy_integrity.py`| 2 - a declared guardrail cannot silently become advisory |
| `test_task_validation.py` | versioning + structural validation of `task.yml` |
| `test_check_guardrails.py`| 3 - typed gate evidence, traceability, backfills |
|                           | 5 - human approvals for irreversible work |
| `test_tdd_evidence.py`    | 1 + 3 - tdd-red/green honesty + registry upsert |
| `test_spike_safety.py`    | 4 - Spike conclusion, no production changes, graduation linkage |
| `test_ci.py`              | 6 - `compass ci` exit-code aggregation |
| `test_modes.py`           | 7 - enforced vs advisory adoption mode |
| `test_calibration.py`     | the Needle's feedback loop - re-frame log and trend signal |
| `test_house_style.py`     | this repository's own writing invariants (strategy S7) - not a safety-contract guarantee |

## Fixtures

`tests/fixtures/routes/` holds six YAML files declaring (readings, expected)
pairs that one parameterised test asserts the CLI's `route evaluate --json`
output matches. To add a new edge case, drop in another YAML - no test code
change needed.

## Hermeticism

Every test gets a fresh temp project from the `project` fixture - a copy of
the shipped `governance/`, an empty `.compass/work/`, and `.compass/config.yml`
set to `mode: enforced`. Tests that need a different mode write the config
file themselves; tests that mutate governance use the `edit_governance`
fixture, which only touches the temp copy.
