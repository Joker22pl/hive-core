# HIVE Core — Architecture

> **Status:** H1 closed (Device Discovery — USB/serial/SQLite registry/locks).
> H2+ (HIVE-IO firmware, flashing, SSH, REST API) still planned.
> **Źródło prawdy:** [`vision.md`](vision.md).

## 1. Cel

HIVE Core jest warstwą wykonawczą dla operacji sprzętowych w projektach robotycznych
Jokera. Daje HARE (i operatorowi) spójne, bezpieczne API do:

- wykrywania i jednoznacznej identyfikacji urządzeń,
- rezerwacji zasobów,
- budowania, wersjonowania i flashowania firmware,
- wykonywania profili weryfikacyjnych,
- odzyskiwania urządzeń po błędach,
- zbierania **Evidence Bundle** dla każdej istotnej operacji.

HIVE Core **nie podejmuje decyzji inżynierskich** — to robi HARE. HIVE Core zapewnia,
że każda operacja sprzętowa jest:

- jednoznacznie autoryzowana (lock + właściciel),
- odwracalna w granicach rozsądku (rollback do `known-good`),
- obserwowalna (logi + evidence bundle),
- bezpieczna (stan bezpieczny HIVE-IO wymuszony sprzętowo).

## 2. Diagram wysokopoziomowy (C4 — Level 1 / Level 2)

```
┌───────────────┐    ┌─────────────────────────────┐    ┌────────────────┐
│   HARE /      │    │        HIVE Core            │    │  HIVE-IO       │
│   Operator    │───▶│ (gajaserv, Python 3.12)     │───▶│  (RPi Pico)    │
│ (CLI / REST)  │    │                              │    │ USB CDC + JSON │
└───────────────┘    └─────────────────────────────┘    └────────────────┘
                              │   │   │   │   │
                              ▼   ▼   ▼   ▼   ▼
                          [Device][Host][Artifact][Evidence][Lock] DB
                              │   │   │
                              ▼   ▼   ▼
                          USB / Serial / SSH / picotool / esptool
                              │   │   │   │
                              ▼   ▼   ▼   ▼
                        ┌──────────────────────────────┐
                        │  Devices under test          │
                        │  • ESP32-S3 (motor, sensor)  │
                        │  • RP2040 (test target)      │
                        │  • Linux hosts (NUC, Jetson) │
                        └──────────────────────────────┘
```

HIVE Core jest jedynym punktem, przez który HARE wykonuje operacje sprzętowe.
HIVE-IO jest warstwą sprzętową wymuszającą bezpieczne stany zasilania, RESET, BOOT,
`MOTOR_ENABLE` i E-stop — niezależnie od stanu HARE/HIVE Core.

## 3. Moduły HIVE Core

| Moduł | Zakres | H0 |
|-------|--------|----|
| `hive.cli` | CLI (Typer) — szkielety komend | ✅ |
| `hive.discovery` | USB / serial / SSH detection | szkielet (interfejs + klasy statusów) |
| `hive.registry` | Ładowanie / walidacja / zapis manifestów | ✅ (logika + walidacja) |
| `hive.artifacts` | Build / hash / wersja / zapis artefaktów | szkielet (interfejs + model danych) |
| `hive.adapters.usb` | USB transport (pyudev) | szkielet |
| `hive.adapters.serial` | Serial transport (pyserial) | szkielet |
| `hive.adapters.esp32` | ESP32 flashing (esptool) | szkielet |
| `hive.adapters.rp2040` | RP2040 flashing (UF2 / picotool) | szkielet |
| `hive.adapters.ssh` | SSH transport (paramiko) | szkielet |
| `hive.verification` | Egzekucja profili weryfikacyjnych | szkielet |
| `hive.locking` | Resource locks z lease | ✅ (H0 in-memory + JSON; H1 SqliteLockStore + sweeper) |
| `hive.recovery` | Strategie recovery per klasa urządzenia | szkielet |
| `hive.evidence` | Generowanie Evidence Bundle | szkielet |
| `hive.database` | SQLite state store (registry + locks) | ✅ H1 (DeviceRegistry + LockRecord + migration 0001) |
| `hive.io_controller` | Klient HIVE-IO (USB CDC + JSON Lines) | szkielet |
| `hive.common` | Modele współdzielone, logowanie, błędy | ✅ |

H0 dostarcza pełne **modele danych** i **interfejsy** dla wszystkich modułów;
implementacje I/O (USB, serial, SSH, flashing) są świadomie szkieletowe i rzucają
`NotImplementedError` z jasnym komunikatem zwracającym uwagę na etap, w którym
funkcjonalność zostanie zaimplementowana.

## 4. Przepływ operacji (high-level)

```
wykrycie urządzenia
  → hive.discovery.scan()                # ✅ H1: real USB/serial (pyudev + pyserial)
  → status identyfikacji (MATCH_CONFIRMED / AMBIGUOUS / UNKNOWN / ...)
  → jeśli !MATCH_CONFIRMED → STOP (refuse to flash)

rezerwacja
  → hive.locking.acquire(device_id, owner, session_id)
  → lease_expires_at + heartbeat

przygotowanie bezpiecznego stanu
  → hive.io_controller.safe_state()      # H2+: real HIVE-IO
  → potwierdzenie MOTOR_ENABLE=OFF

budowa artefaktu
  → hive.artifacts.build(spec) → artifact_id + sha256
  → manifest artefaktu (registry/ w pamięci / DB)

flashowanie / deploy
  → hive.adapters.<class>.flash(...)
  → zbieranie logów

weryfikacja
  → hive.verification.run(profile_id, device_id) → result

evidence bundle
  → hive.evidence.create(...) → bundle_id + path

zwolnienie locka
  → hive.locking.release(device_id, session_id)

w razie błędu → hive.recovery.run(strategy, device_id) → recovery_log
```

## 5. Identyfikacja urządzenia

Pełny opis w [`device-identity.md`](device-identity.md). Skrót:

- Identyfikacja opiera się na kombinacji cech:
  - USB VID/PID, serial number (jeśli dostępny),
  - ścieżka `/dev/...` (niestabilna, tylko pomocnicza),
  - fingerprint klucza SSH (dla hostów),
  - metadane z poprzednich sesji (cached w rejestrze).
- Manifest w `registry/` łączy te cechy z logicznym `device_id` + `project` + `role`.
- **Nigdy** nie używamy samego `/dev/ttyUSB0` jako identyfikatora.

## 6. Resource locking

Pełna specyfikacja w [`../schemas/...`] + `hive.locking`. Każda operacja sprzętowa:

1. uzyskuje lock (`acquire(device_id, owner, session_id, ttl)`),
2. posiada właściciela i identyfikator sesji,
3. ma lease z czasem wygaśnięcia (TTL),
4. odnawia lease przez heartbeat (opcjonalnie — w H0 lease nie jest auto-renewed),
5. zwalnia lock jawnie lub po wygaśnięciu,
6. obsługuje porzucone locki (sweeper — ✅ H1: `LockSweeper`).

H0 dostarcza model i logikę in-memory + opcjonalny JSON store (`hive.locking.store.JsonLockStore`).
H1 dostarcza `SqliteLockStore` (persistent) + `LockSweeper` (auto-cleanup).

## 7. Evidence bundle

Pełna specyfikacja w [`verification-model.md`](verification-model.md) i schema
[`../schemas/evidence-bundle.schema.json`](../schemas/evidence-bundle.schema.json).
Evidence bundle jest generowany dla każdej istotnej operacji i zawiera:

- identyfikator operacji (`run_id`),
- manifest urządzenia,
- artefakt i jego hash,
- commit Git + dirty state,
- wersje narzędzi (Python, esptool, picotool, paramiko, itd.),
- komendy i parametry,
- logi budowania / flashowania / urządzenia,
- wyniki poszczególnych kroków weryfikacji,
- zdarzenia bezpieczeństwa,
- decyzje recovery,
- czas rozpoczęcia / zakończenia,
- finalny status.

H0 dostarcza **model danych** i **interfejs** (`hive.evidence.EvidenceBundle.to_dict()`,
`write_json()`). Logika zbierania logów urządzenia w trakcie złożonych operacji
jest poza H0.

## 8. HIVE Core ↔ HIVE-IO — protokół

Pełna specyfikacja w [`io-protocol.md`](io-protocol.md). W skrócie:

- transport: USB CDC,
- format: JSON Lines (jeden JSON na linię, `\n`-terminated),
- każde polecenie ma `request_id`, nazwę komendy, parametry,
- odpowiedź ma `request_id`, `result` (`ok` / `error`), `observed_state`,
- wersjonowany protokół (`protocol_version: "0.1.0"`),
- przewidziane przyszłe rozszerzenia: CRC, format binarny, uwierzytelnianie,
  wiele kontrolerów, komunikacja sieciowa przez gateway.

## 9. Granice HARE ↔ HIVE

> HARE decyduje, **co** i **kiedy** — HIVE wykonuje, **jak** i **na czym**.

HARE ma dostęp do **wysokopoziomowego API** HIVE Core:

- `identify_device()` → status identyfikacji
- `reserve_device()` / `release_device()`
- `build_artifact()` → manifest artefaktu
- `flash_device()` → evidence
- `deploy_to_linux()`
- `run_verification()`
- `collect_evidence()`
- `recover_device()` / `rollback_device()`
- `enter_safe_state()`

HARE **NIE MA** dostępu do:

- surowych GPIO,
- przekaźników, load switchów, MOSFET-ów,
- linii BOOT / RESET,
- bezpośredniego sterowania `MOTOR_ENABLE`,
- `/dev/tty*` (porty szeregowe),
- SSH do hostów (idzie przez HIVE).

Te granice są częścią **kontraktu** HIVE Core, egzekwowanego na poziomie
architektury (brak takich endpointów w publicznym API) oraz na poziomie procesu
(HIVE działa z dedykowanym kontem z ograniczonymi uprawnieniami).

## 10. Bezpieczeństwo — skrót

Pełny opis w [`safety-model.md`](safety-model.md). Najważniejsze:

- **Brak `MATCH_CONFIRMED` = zakaz flashowania.**
- `MOTOR_ENABLE=OFF` wymuszone sprzętowo przez HIVE-IO.
- Aktywny E-stop > każde polecenie programowe.
- Utrata heartbeat / kontroli linku → natychmiastowy `safe_state`.
- Recovery z limitem prób + eskalacja do człowieka.
- Locki z TTL zapobiegają zombie operacjom.
- Evidence bundle jako audyt.

## 11. Out-of-scope H0

Następujące elementy **nie są** dostarczane w H0 (świadomie):

- real USB/serial discovery (klasa `DiscoveryService` jest szkieletem),
- real SSH / flashing / artefact building (adapter classes są szkieletami),
- SQLite state store,
- REST API (architektura jest gotowa — FastAPI dodany w H5+),
- production-grade recovery execution (interfejs jest, implementacja w H3+),
- real HIVE-IO firmware (oddzielne repo `hive-io`, H2),
- Hardware-in-the-Loop (H6).

H0 to **fundament**: modele danych, dokumentacja, szkielety modułów, szkielety CLI,
testy walidacji modeli. Wszystko, co nie jest krytyczne dla tych fundamentów,
jest odłożone na właściwy etap roadmapy.

## 12. Decyzje architektoniczne (linki)

- [`adr/0001-hive-scope-and-boundaries.md`](adr/0001-hive-scope-and-boundaries.md) — zakres HIVE i granica HARE
- [`adr/0002-stack-choice-python-pydantic.md`](adr/0002-stack-choice-python-pydantic.md) — Python 3.12 + Pydantic v2
- [`adr/0003-device-identity-model.md`](adr/0003-device-identity-model.md) — model identyfikacji
- [`adr/0004-io-controller-as-separate-pico.md`](adr/0004-io-controller-as-separate-pico.md) — HIVE-IO jako osobny Pico
- [`adr/0005-no-direct-hardware-from-hare.md`](adr/0005-no-direct-hardware-from-hare.md) — zakaz bezpośredniego hardware z HARE
- [`adr/0006-protocol-versioning.md`](adr/0006-protocol-versioning.md) — wersjonowanie protokołu HIVE-IO
