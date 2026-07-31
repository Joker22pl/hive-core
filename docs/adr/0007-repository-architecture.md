| id | status | date | owners |
|---|---|---|---|
| 0007 | Accepted | 2026-07-30 | gaja-robotics (profil Hermes) |

# ADR-0007: Repository Architecture — `hive-core` / `hive-io` / `gaja-projekty`

## Context

HIVE consists of three units that evolve semi-independently:

* **`hive-core`** — Python 3.12 framework that orchestrates hardware
  operations. Touched on every workflow change.
* **`hive-io`** — embedded C/Pico SDK firmware + hardware specs for the
  controller board. Touched only when the IO protocol or the
  controller hardware changes.
* **`gaja-projekty`** — central hub that indexes all Joker's projects.
  Receives cross-project updates when a project status changes.

H0 mistakenly kept all three as subdirectories of a single Git repo
(`Joker22pl/gaja-projekty`). The audit (`HIVE-H0-ASSESSMENT-REPORT.md`,
finding HIGH-3) flagged this as a structural defect:

* Hive-core PRs are not separable from hive-io PRs.
* External visibility (PRs, Issues, Releases) is degraded.
* Branch protection cannot be per-project.
* CI cannot be per-project.
* The hub gets noise from the inner repos.

## Decision

**Each project is its own Git repository.** The hub points to it; it
does not contain its source.

| Project | Repo URL | Style |
|---|---|---|
| `hive-core` | `https://github.com/Joker22pl/hive-core` | standalone |
| `hive-io` | `https://github.com/Joker22pl/hive-io` | standalone |
| `gaja-projekty` | `https://github.com/Joker22pl/gaja-projekty` | hub (index only) |

The hub contains:

* a top-level `README.md` with a table linking to each project,
* `hive-core/` and `hive-io/` as **stub directories** carrying only
  a 1-line `README.md` pointing outward (`> This project has been
  moved to https://github.com/Joker22pl/hive-core — please clone
  there.`),
* shared meta (`WORKFLOW.md`, `templates/`, `.pre-commit-config.yaml`).

We **do not** use git submodules. Reasons:

* Submodules add cognitive overhead without simplification here.
* H0+H1 work is small enough that operators can clone three repos
  without a unified superproject.
* Submodules complicate the existing CI that already runs on the hub.

## Tracking Core–IO compatibility

Compatibility between `hive-core` and `hive-io` is governed by:

* `PROTOCOL_VERSION` (SemVer) in `hive.io_controller.protocol` (Core)
  and `HIVE_IO_PROTOCOL_VERSION` in `hive_io/protocol.h` (IO).
* Same MAJOR → compatible at the protocol layer.
* MINOR support is forward-compatible (Core may have higher MINOR).
* PATCH is always compatible.

When MAJOR changes, both repos must be updated atomically:

1. Bump `PROTOCOL_VERSION` in `hive-core` and `HIVE_IO_PROTOCOL_VERSION`
   in `hive-io` in **separate commits** in their respective repos.
2. The first commit on either side may add a new MAJOR while the
   other side still supports the **previous** MAJOR (grace period).
3. The new MAJOR is considered active only after both sides have
   bumped.

## Versioning

Each project has its own version number (`hive-core` 0.1.0, `hive-io`
0.1.0 today). The version is independent except for the protocol
version, which is shared.

## Breaking-change rules

A breaking change in the protocol requires:

1. A new ADR in **both** `hive-core/docs/adr/` and `hive-io/docs/adr/`
   (with the same identifier, e.g. `0007-protocol-v2.md`).
2. A cross-reference in both repos' release notes.
3. A grace period of at least **two minor releases** before the old
   MAJOR is dropped (documented in the new ADR).

## Integration tests

The planned `hive-integration` repo (separate, H5+) will:

1. Clone both `hive-core` and `hive-io` at fixed tags.
2. Build `hive-io` against Pico SDK.
3. Run `hive-core` integration tests against the real firmware.
4. Cross-check `PROTOCOL_VERSION` equality.

For H0 there is no such test suite; the consistency check is enforced
by the CI workflow (`.github/workflows/hive-io-build.yml::protocol-consistency-check`).

## Hub update rules

When a project is updated, the hub's `README.md` is updated in the
**next commit** to that project's repo with:

* the latest commit SHA,
* the latest tag,
* the status icon (🟢 / 🟡 / 🔴 / ⚪).

The hub's CI does not run on `hive-core/**` or `hive-io/**` paths
(those are ignored — the inner repos' own CI is authoritative).

## Consequences

Positive:

* Each project has its own PRs, Issues, Releases, CI.
* Branch protection is per-project.
* Cross-project coupling is explicit (protocol version), not hidden.

Negative:

* Operators must clone three repos instead of one.
* Cross-project CI requires a separate `hive-integration` repo.

## Alternatives considered

* **Submodules.** Rejected: cognitive overhead, no clear benefit at
  this scale.
* **Monorepo with multiple pnpm-style workspaces.** Rejected: the
  toolchain is Python + C, no workspace manager is needed.
* **One mega-repo per Joker.** Rejected: defeats the entire
  ecosystem convention (each project = own repo).
