# Safety Model — HIVE Core

> **Najważniejsza zasada:** Brak jednoznacznej identyfikacji urządzenia = bezwzględny
> zakaz flashowania. To jest hard rule, nie rekomendacja.

## 1. Warstwy bezpieczeństwa

HIVE Core utrzymuje bezpieczeństwo na czterech warstwach. Każda warstwa jest
niezależna — awaria jednej nie powoduje awarii pozostałych.

| Warstwa | Co zapewnia | Gdzie żyje |
|---------|-------------|------------|
| L1. Identyfikacja | Tylko `MATCH_CONFIRMED` → flash | `hive.registry`, `hive.discovery` |
| L2. Resource lock | Brak konkurujących operacji | `hive.locking` |
| L3. Bezpieczny stan | `MOTOR_ENABLE=OFF`, zasilanie off, BOOT inactive | `hive.io_controller` → HIVE-IO |
| L4. E-stop + watchdog | Fizyczny kill + sprzętowy timeout | HIVE-IO + mikrokontroler testowany |

## 2. Stany identyfikacji

Zdefiniowane w `hive.common.status.IdentificationStatus`:

| Status | Znaczenie | Flash dozwolony? |
|--------|-----------|-------------------|
| `MATCH_CONFIRMED` | Wszystkie cechy urządzenia pasują do manifestu | ✅ tak (po lock + safe state) |
| `MATCH_AMBIGUOUS` | Cechy pasują do >1 manifestu | ❌ nie |
| `DEVICE_UNKNOWN` | Brak manifestu dla tego urządzenia | ❌ nie |
| `DEVICE_OFFLINE` | Urządzenie zniknęło | ❌ nie |
| `DEVICE_BUSY` | Urządzenie ma locka innego właściciela | ❌ nie |
| `PROJECT_MISMATCH` | Urządzenie przypisane do innego projektu | ❌ nie |
| `ROLE_MISMATCH` | Manifest istnieje, ale rola się nie zgadza | ❌ nie |
| `FIRMWARE_INCOMPATIBLE` | Artefakt nie jest kompatybilny z device.type | ❌ nie |
| `RECOVERY_REQUIRED` | Urządzenie wymaga recovery zanim pójdzie dalej | ❌ (recovery first) |
| `SAFETY_INTERLOCK_OPEN` | E-stop / bezpiecznik otwarty | ❌ nie |
| `ESTOP_ACTIVE` | Fizyczny E-stop wciśnięty | ❌ nie |

Tylko `MATCH_CONFIRMED` zezwala na autonomiczne flashowanie. Każdy inny status
**musi** być eskalowany do człowieka lub rozwiązany przez recovery.

## 3. Resource locking — minimalne wymagania

Każda operacja sprzętowa MUSI przejść przez `hive.locking.acquire(...)`:

```python
lock = hive.locking.acquire(
    device_id="esp32s3-imp2-motor-01",
    owner="hare",                        # kto — hare / operator:user / hive
    session_id="hive-run-20260730-001",  # identyfikator sesji
    operation="firmware-verification",
    ttl_seconds=900,
)
# ... operacja ...
hive.locking.release(device_id="...", session_id="...")
```

Lock posiada:

- `device_id` — jednoznaczny identyfikator urządzenia,
- `owner` — właściciel (zazwyczaj `"hare"` lub `"operator:<username>"`),
- `session_id` — identyfikator sesji (UUID lub deterministyczny),
- `operation` — nazwa operacji (np. `"flash"`, `"verify"`, `"recovery"`),
- `acquired_at` — timestamp,
- `expires_at` — timestamp wygaśnięcia lease,
- `heartbeat_at` — ostatni heartbeat (opcjonalnie w H0).

H0 dostarcza `InMemoryLockStore` + `JsonLockStore`. Sweeper porzuconych locków
jest zaplanowany na H1.

## 4. Bezpieczny stan (HIVE-IO)

HIVE-IO startuje w stanie:

```text
MOTOR_ENABLE = OFF
motor power = OFF
autonomous motion = FORBIDDEN
BOOT signals = INACTIVE
RESET signals = RELEASED
```

Utrata komunikacji z HIVE Core (heartbeat > threshold) → HIVE-IO wymusza
`safe_state()` samodzielnie:

1. natychmiastowe `MOTOR_ENABLE = OFF`,
2. power off na kanałach napędowych (POWER_MOTOR_* → OFF; logika może zostać),
3. RESET lines RELEASED,
4. BOOT lines INACTIVE,
5. zgłoszenie `CONTROL_LINK_LOST` (po powrocie komunikacji → logowane w evidence).

Aktywny E-stop ma **wyższy priorytet** niż polecenia HIVE Core. HIVE-IO ignoruje
`motor_enable_set true` jeśli `estop_status == ACTIVE`.

## 5. Flash — sekwencja bezpieczeństwa

Dla każdej operacji flash:

1. Sprawdź `IdentificationStatus == MATCH_CONFIRMED`. Jeśli nie → `refuse`.
2. Sprawdź `lock.acquire(...)`. Jeśli `DEVICE_BUSY` → `refuse`.
3. Sprawdź `estop_status`. Jeśli `ESTOP_ACTIVE` → `refuse`.
4. Wyślij `safe_state()` do HIVE-IO. Potwierdź `MOTOR_ENABLE=OFF`.
5. Wykonaj `power_cycle(target)` jeśli to wymagane.
6. Wykonaj `enter_bootloader(target)`.
7. Flash artefaktu.
8. `reset(target)`.
9. Uruchom profil weryfikacyjny.
10. Zbierz `evidence_bundle`.
11. `lock.release(...)`.

Jeśli którykolwiek krok się nie powiedzie:

- zgłoś błąd,
- wykonaj `recovery.run(...)` zgodnie ze strategią urządzenia,
- jeśli recovery się powiódł → wznowienie; jeśli nie → eskalacja.

## 6. Recovery — granice

Recovery NIE MOŻE:

- wykonywać się w nieskończonej pętli,
- flashować czegoś innego niż `known_good_artifact` (chyba że to zatwierdzone recovery),
- ignorować E-stop,
- pomijać lock.

Recovery MUSI:

- mieć `max_attempts` (domyślnie 3),
- po przekroczeniu `max_attempts` → eskalacja do człowieka + `EVIDENCE_BUNDLE`,
- zapisywać każdą próbę w evidence bundle,
- przerywać na aktywny E-stop.

## 7. Audyt i obserwowalność

Każda istotna operacja → `evidence_bundle` zapisywany do `artifacts/evidence/<bundle_id>/`.
Evidence bundle jest:

- obiektem JSON (schema `evidence-bundle.schema.json`),
- z haszem SHA-256 swojego ciała (dla integralności),
- z linkiem do commit Git + dirty state,
- z wersjami wszystkich użytych narzędzi.

H0 dostarcza model + serializer. Generowanie pełnych bundle'y w runtime jest
zaplanowane na H3.

## 8. Co nie wchodzi w zakres H0

- Real HIVE-IO firmware (osobne repo `hive-io`).
- Real flashing (esptool / picotool integracja).
- Real SSH execution.
- Sweeper porzuconych locków (H1+).
- SQLite persistence (H1+).

H0 dostarcza **model bezpieczeństwa** i **szkielety implementacji**. Pełne
egzekwowanie bezpieczeństwa pojawia się razem z I/O (H1+).
