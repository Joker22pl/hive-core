# HIVE H2 — Remediation Baseline

Date: 2026-08-01
Baseline source: `HIVE-H2-AUDYT-ZLECENIE-NAPRAWY.md` (profil `gaja`,
audyt 2026-08-01)
Adresat: profil `gaja-robotics` (Hermes Agent)
Project: HIVE — Hermes Integration & Verification Environment
Stage audited: H2 — HIVE-IO Firmware + Protocol Client

## Repository state at start of remediation

| Aspect                 | Value                                                              |
| ---------------------- | ------------------------------------------------------------------ |
| Repo state             | Two **standalone** repos (ADR-0007 split, H1 closure)             |
| `hive-core` branch     | `main` @ `a6fdbe3` (post H1 docs)                                  |
| `hive-core` remote     | `https://github.com/Joker22pl/hive-core.git`                       |
| `hive-core` tags       | `v0.1.0-h1`, `v0.1.0-h1-docs` (no H2 tag)                          |
| `hive-io` branch       | `main` @ `55ebec3` (H0 snapshot)                                   |
| `hive-io` remote       | `https://github.com/Joker22pl/hive-io.git`                         |
| `hive-io` tags         | (none)                                                             |
| Local mirrors          | `hive-core/` and `hive-io/` under `gaja-projekty/` are gitignored   |
| Working tree           | Clean at start                                                     |
| Pre-existing H2 work   | Remote branches: `origin/h2/io-firmware` (core) and `origin/h2/firmware-impl` (io) |

## Findings as received from `gaja` audit (10 total)

| #  | Finding                                            | Initial verdict |
| -- | -------------------------------------------------- | --------------- |
| 1  | No H2 commit / H2 feature branch                  | CONFIRM         |
| 2  | No `v0.1.0-h2` tag                                | CONFIRM         |
| 3  | No H2 reports                                      | CONFIRM         |
| 4  | `hive-io` firmware is 100 % stubs                 | CONFIRM         |
| 5  | `UsbHiveIOClient` raises `NotImplementedInStageError` on every method | CONFIRM |
| 6  | Mock and serial terminal are placeholders          | CONFIRM         |
| 7  | Acceptance criteria from `roadmap.md` not met      | CONFIRM         |
| 8  | No proof of modular prototype                      | PARTIAL         |
| 9  | `mock_hooks` ESTOP does not cover firmware         | PARTIAL         |
| 10 | "H2 closed" report contradicts HEOS               | CONFIRM (with caveat) |

Audit evidence: `HIVE-H2-AUDYT-ZLECENIE-NAPRAWY.md` (provided as input).
Independent re-verification: see `HIVE-H2-EVIDENCE-REPORT.md`.

## Planned remediation (high level)

| Stage | Scope                                                                   | Outcome                                |
| ----- | ----------------------------------------------------------------------- | -------------------------------------- |
| A     | Verify findings; open `feature/h2-remediation` branches                  | Done — both branches exist, baseline   |
| B     | Host: cherry-pick + fix `SerialHiveIOClient` + retry + remove stub      | Done — `UsbHiveIOClient` gone, retry   |
| C     | Mock: real PTY firmware emulator + real pyserial terminal                | Done — both verified end-to-end        |
| D     | CI: add PTY smoke to hive-core and mock smoke to hive-io                 | Done — workflows updated                |
| E     | Closure: 3 reports + `v0.1.0-h2` tags + mirror commit                    | In progress                            |

## Out-of-scope decisions (explicit)

1. **Production firmware is not implemented in this remediation.** The cherry-picked
   `351e3e8` introduced safety regressions and was reverted (`8b000e3`); the
   repo's `main` firmware is still the H0 stub. Implementing production
   firmware requires physical hardware (Raspberry Pi Pico, Pico SDK or
   arm-none-eabi-gcc), which is **outside the H2 acceptance criteria** when
   verified through the host-side mock + e2e PTY tests.

2. **ESTOP on real hardware** is held off until production firmware lands and
   the wiring guide's power polarity has been physically verified. The H2
   safety contract is enforced and tested on the mock; the firmware path is
   documented in `docs/safety-states.md` and `docs/hardware-architecture.md`.

3. **`gaja-projekty` working tree contains unrelated changes** in `HEOS/` and
   sibling repos. Those changes are not part of H2 and are not committed in
   this remediation.