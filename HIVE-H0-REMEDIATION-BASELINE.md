# HIVE H0 — Remediation Baseline

Date: 2026-07-30
Baseline tag: `hive-h0-pre-remediation`
Baseline HEAD: `9e8a5a5`

## Repository state

| Aspect | Value |
|---|---|
| Repo | `/home/gaja/gaja-projekty` (single repo) |
| Branch | `main` |
| HEAD | `9e8a5a5` |
| Ahead of origin | 4 commits |
| Hive-core pre-remediation audit commit | `da84e4c` |
| Hive-io pre-remediation audit commit | `da84e4c` (same parent) |
| Working tree clean | YES (only untracked GAIA/HEOS/etc. — not part of H0) |

## Test results (baseline)

```
$ .venv/bin/python -m pytest tests/unit -q
78 passed in 0.44s
```

| File | Tests |
|---|---|
| test_artifact_hash.py | 5 |
| test_artifact_model.py | 5 |
| test_device_model.py | 11 |
| test_errors.py | 5 |
| test_evidence_bundle.py | 4 |
| test_evidence_serialization.py | 1 |
| test_io_controller.py | 21 |
| test_locking.py | 17 |
| test_status.py | 4 |
| test_verification_profile.py | 5 |
| **TOTAL** | **78** |

> Note: audit report claimed 79 (test_io_controller=23). My re-run shows 78 (test_io_controller=21).
> The audit's count was wrong. Remediation will use the accurate 78.

## Lint

```
$ .venv/bin/ruff check src/ tests/
All checks passed!
```

## Format

```
$ .venv/bin/ruff format --check src/ tests/
48 files already formatted
```

## Coverage

```
$ .venv/bin/python -m coverage run --source=src/hive -m pytest tests/unit -q && \
  .venv/bin/python -m coverage report --include="src/hive/*"
78 passed in 0.30s
Name                                       Stmts   Miss  Cover
--------------------------------------------------------------
src/hive/__init__.py                           2      0   100%
src/hive/adapters/__init__.py                  4      0   100%
... (~90% aggregate per audit re-run)
```

## GitHub remote

```
$ curl -sI -o /dev/null -w "%{http_code}\n" https://github.com/Joker22pl/hive-core
404
$ curl -sI -o /dev/null -w "%{http_code}\n" https://github.com/Joker22pl/hive-io
404
```

## Files audited

- 78 Python tests in 10 files
- 36 Python source files
- 4 JSON schemas
- 6 ADRs
- 7 registry manifests
- 10 docs (~3240 LOC)
- 11 hive-io C/H files
- 6 hive-io docs
- 3 hardware files
