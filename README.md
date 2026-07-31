# HIVE Core

> **Hermes Integration & Verification Environment — Core**
> **Wersja:** v0.1.0 (H1 — Device Discovery)
> **Status:** 🟢 H1 closed (314 tests, 92% coverage, CI green)
> **H0 metrics:** 200 unit tests pass, ruff clean, coverage 96%
> **H1 metrics:** 314 tests pass (unit + integration), ruff clean, coverage 92%
> **Evidence:** `HIVE-H1-EVIDENCE-REPORT.md`
> **Owner:** gaja-robotics (profil Hermes)
> **HEOS:** oparty na `HEOS/CONSTITUTION.md` v1.5+
> **Licencja:** MIT

**HIVE Core** to warstwa sterująca bezpiecznego środowiska integracji, programowania,
flashowania, testowania, diagnostyki i odzyskiwania urządzeń wykorzystywanych w projektach
robotycznych Jokera (IMP2, ARP-AGRI, inne). HIVE Core działa na serwerze `gajaserv`
(Intel NUC, Ubuntu Server 24.04) i jest wywoływane przez autonomicznego agenta inżynierskiego
**HARE** (Hermes Autonomous Robotics Engineer).

HIVE Core:

- identyfikuje urządzenia (USB VID/PID, serial, ścieżki, fingerprinty SSH),
- prowadzi rejestr urządzeń w formie deklaratywnych manifestów (YAML + JSON Schema),
- buduje, hashuje (SHA-256), wersjonuje i podpisuje artefakty firmware,
- rezerwuje zasoby (`resource locking` z lease i właścicielem),
- flashuje ESP32-S3, RP2040, deployuje na hosty Linux przez SSH,
- wykonuje zadeklarowane profile weryfikacyjne,
- generuje **Evidence Bundle** dla każdej istotnej operacji,
- obsługuje recovery i rollback do `known-good`,
- steruje sprzętowym kontrolerem stanowiska **HIVE-IO** (osobne Pico, USB CDC + JSON Lines),
- udostępnia CLI (`hive`) oraz wewnętrzne Python API; REST API planowane (poza H0).

## Granica odpowiedzialności

> **HARE** decyduje, *jak* wykonać pracę inżynierską.
> **HIVE** wykonuje wszystkie operacje sprzętowe przez kontrolowane API.
> **HARE nigdy nie dotyka** surowych GPIO, przekaźników, linii BOOT/RESET, portów
> `/dev/tty*` ani nie wykonuje poleceń na hostach SSH — wszystko idzie przez HIVE.

## Status projektu

| Etap | Status | Opis |
|------|--------|------|
| H0 | 🟢 | Fundament — modele danych, dokumentacja, szkielety CLI, brak prawdziwego flashowania |
| H1 | 🟢 | Device Discovery — USB/serial (pyudev/pyserial), SQLite registry, lock sweeper |
| H2 | ⚪ | HIVE-IO firmware, protokół, heartbeat, E-stop |
| H3 | ⚪ | Flashing + Artifact Registry + rollback |
| H4 | ⚪ | Linux / ROS 2 przez SSH |
| H5 | ⚪ | Integracja z HARE |
| H6 | ⚪ | Hardware-in-the-Loop |
| H7 | ⚪ | Distributed HIVE (zdalne gatewaye) |

Pełna roadmapa w [`docs/roadmap.md`](docs/roadmap.md).

## Co dostarcza H0

- Architektura i model bezpieczeństwa ([`docs/architecture.md`](docs/architecture.md), [`docs/safety-model.md`](docs/safety-model.md))
- Model urządzenia, artefaktu, profilu weryfikacyjnego, evidence bundle ([`docs/`](docs/))
- JSON Schema dla `device`, `artifact`, `verification-profile`, `evidence-bundle` ([`schemas/`](schemas/))
- Deklaratywne przykłady rejestru urządzeń ([`registry/`](registry/))
- Specyfikacja protokołu HIVE Core ↔ HIVE-IO ([`docs/io-protocol.md`](docs/io-protocol.md))
- Threat model ([`docs/threat-model.md`](docs/threat-model.md))
- Szkielety modułów Python (`src/hive/`) — logika bez I/O w H0
- Szkielety CLI (`src/hive/cli/`) — kontrakt i stub komend
- Testy walidacji schematów i smoke testy modeli (`tests/`)
- ADR ([`docs/adr/`](docs/adr/))

## Stack

- Python 3.12
- `pydantic` v2 — walidacja modeli
- `pyudev`, `pyserial` — detekcja USB/serial (H1+)
- `paramiko` / `openssh` — SSH (H4+)
- `esptool`, `picotool` — flashing (H3+)
- `typer`, `rich` — CLI
- `pytest` — testy
- `jsonschema` — walidacja manifestów
- SQLite — baza stanu operacyjnego (H1+)
- JSON Schema + YAML jako źródło prawdy dla manifestów

## Jak uruchomić (H0)

```bash
# 1. Klon / środowisko
cd hive-core
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Testy modeli + schematów
pytest tests/unit -q

# 3. CLI (szkielety — w H0 wiele komend rzuci NotImplementedError z komunikatem)
hive system status
hive device scan
hive device list
hive io status
```

## Struktura katalogów

```
hive-core/
├── README.md
├── LICENSE
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml
├── pyproject.toml
├── docs/
│   ├── vision.md                ← kopia oryginalnego dokumentu wizji (verbatim)
│   ├── architecture.md
│   ├── safety-model.md
│   ├── device-identity.md
│   ├── artifact-lifecycle.md
│   ├── verification-model.md
│   ├── recovery-model.md
│   ├── io-protocol.md
│   ├── threat-model.md
│   ├── roadmap.md
│   └── adr/                     ← Architecture Decision Records
├── schemas/
│   ├── device.schema.json
│   ├── artifact.schema.json
│   ├── verification-profile.schema.json
│   └── evidence-bundle.schema.json
├── registry/                    ← manifesty urządzeń, hostów, programatorów (declarative)
│   ├── devices/
│   ├── boards/
│   ├── hosts/
│   └── programmers/
├── src/hive/
│   ├── cli/
│   ├── discovery/               ← USB/serial/SSH detection (szkielety w H0)
│   ├── registry/                ← load/save/validate manifestów
│   ├── artifacts/               ← build/hash/version artefaktów (szkielety w H0)
│   ├── adapters/                ← device-specific adapters (H1+)
│   │   ├── usb/
│   │   ├── serial/
│   │   ├── esp32/
│   │   ├── rp2040/
│   │   └── ssh/
│   ├── verification/            ← execution profili weryfikacyjnych (szkielety w H0)
│   ├── locking/                 ← resource locks (model + szkielet implementacji w H0)
│   ├── recovery/                ← strategie recovery (szkielety w H0)
│   ├── evidence/                ← evidence bundles (szkielety w H0)
│   ├── database/                ← SQLite state (H1+)
│   ├── io_controller/           ← klient HIVE-IO (szkielety w H0)
│   └── common/                  ← logowanie, błędy, modele współdzielone
├── tests/
│   ├── unit/                    ← testy walidacji schematów, modeli, lockingu
│   ├── integration/             ← (H1+)
│   └── fixtures/
└── examples/
```

## Najważniejsze zasady bezpieczeństwa

> **Brak jednoznacznej identyfikacji urządzenia = bezwzględny zakaz flashowania.**

Pełny opis w [`docs/safety-model.md`](docs/safety-model.md). Poniżej skrót:

1. Identyfikacja opiera się na kombinacji cech (VID/PID, serial, port, fingerprint SSH) +
   rejestrze manifestów — **nigdy** nie tylko na `ttyUSB0` czy `ttyACM0`.
2. Tylko stan `MATCH_CONFIRMED` zezwala na autonomiczne flashowanie.
3. Każda operacja sprzętowa wymaga locka z lease i właścicielem.
4. `MOTOR_ENABLE` musi być wyłączony podczas flashowania; HIVE-IO to wymusza sprzętowo.
5. Aktywny E-stop ma wyższy priorytet niż dowolne polecenie HIVE Core.
6. Utrata heartbeat / kontroli linku → natychmiastowy `safe_state`.
7. Recovery ma limit prób i warunek eskalacji do człowieka.

## HARE — kontrakt API (planowany, nie implementowany w H0)

```text
identify_device        # → device_id + status identyfikacji
reserve_device         # → lease
release_device         # → zwalnia lock
build_artifact         # → artifact_id + sha256
flash_device           # → evidence_bundle_id
deploy_to_linux        # → evidence_bundle_id
run_verification       # → verification_result
collect_evidence       # → bundle
recover_device         # → recovery_log
rollback_device        # → evidence_bundle_id
enter_safe_state       # → confirmation
```

## Konwencje

- Commity po angielsku, format `[tag] description`.
- Tagi: `[init]`, `[add]`, `[fix]`, `[doc]`, `[refactor]`, `[test]`, `[security]`, `[chore]`.
- Każda decyzja architektoniczna → ADR (`docs/adr/000N-title.md`).
- Kod modułowy, testowalny, z obsługą błędów, structured logging.
- `hive` CLI z `typer` + `rich`.

## Linki

- [`hive-io`](../hive-io/) — firmware + hardware kontrolera HIVE-IO
- [HARE](../hare-robotics-engineer/) — autonomiczny agent inżynierski (klient HIVE)
- [HEOS](../HEOS/CONSTITUTION.md) — zasady organizacji wiedzy
- [gaja-projekty](../README.md) — centralny hub projektów

---

_Last updated: 2026-07-30 (H0 bootstrap by Gaja)_
