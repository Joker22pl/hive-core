# Verification Model

> **Źródło prawdy:** [`vision.md`](vision.md) sekcja 14 + schema
> [`../schemas/verification-profile.schema.json`](../schemas/verification-profile.schema.json).

## 1. Czym jest profil weryfikacyjny

**Profil weryfikacyjny** to deklaratywny opis sekwencji kroków, które HIVE
wykonuje na urządzeniu, aby potwierdzić, że artefakt jest gotowy do użycia.
Profile są:

- **deklaratywne** (YAML, nie kod),
- **walidowalne** (JSON Schema),
- **kompozycyjne** (zbiór kroków + preconditions + success/failure policies),
- **rozszerzalne** (H3+ dodaje nowe typy kroków bez zmiany rdzenia).

Profile są podobne do HARE `mission.schema.yaml`, ale żyją w HIVE i dotyczą
tylko hardware (nie logiki biznesowej).

## 2. Profile dostarczane w H0 (szkielety)

| Profile ID | Target type | Cel |
|------------|-------------|------|
| `build-only` | any | Sprawdza, czy artefakt się zbudował (hash, manifest) |
| `flash-and-boot` | microcontroller | Flash + reset + obserwacja boot signature |
| `serial-smoke-test` | microcontroller | Otwiera port, czeka na N linii logu, wychodzi |
| `esp32-basic-health` | esp32-s3-pico | Flash + boot + micro-ROS ping |
| `rp2040-basic-health` | raspberry-pi-pico | UF2 flash + reset + boot signature |
| `microros-connectivity` | esp32-s3-pico | Sprawdza, czy micro-ROS agent łączy się przez USB CDC |
| `linux-ssh-health` | linux_host | SSH ping + `uname -a` + obecność katalogów |
| `ros2-basic-health` | linux_host | `ros2 node list`, `ros2 topic list`, `ROS_DOMAIN_ID` |

Profile `flash-and-boot`, `serial-smoke-test`, `esp32-basic-health`,
`rp2040-basic-health`, `microros-connectivity`, `linux-ssh-health`,
`ros2-basic-health` są **szkieletowe** w H0 — ich kroki są zdefiniowane, ale
realne wykonanie pojawia się w H1–H4.

## 3. Anatomia profilu

```yaml
profile_id: esp32-basic-health
target_type: esp32-s3-pico

preconditions:
  - device_match_confirmed
  - motor_enable_off                # HIVE-IO potwierdza stan
  - artifact_compatible             # artifact.target == device.target

steps:
  - id: enter_bootloader
    type: adapter_call
    adapter: esp32
    method: enter_bootloader
    params:
      via: rom-usb                   # przez ROM bootloader USB
      timeout_s: 5

  - id: flash_artifact
    type: adapter_call
    adapter: esp32
    method: flash
    params:
      artifact_ref: "{{ artifact.artifact_id }}"
      flash_mode: dio
      flash_size: 4mb
      flash_freq: 80m
    timeout_s: 60

  - id: reset_device
    type: adapter_call
    adapter: io
    method: reset_pulse
    params:
      channel: RESET_ESP32_1
      duration_ms: 100

  - id: wait_for_serial
    type: serial_observe
    port: stable_path
    pattern: ".*boot.*"             # regex
    timeout_s: 10

  - id: assert_boot_signature
    type: assertion
    value_artifact: "{{ steps.wait_for_serial.first_match }}"
    expected: "ESP-ROM:esp32s3"
    on_failure: classify_failure

  - id: collect_serial_logs
    type: serial_collect
    port: stable_path
    duration_s: 5
    output: logs/serial-after-boot.log

success:
  all_steps_passed: true
  collect_evidence: true

failure:
  collect_evidence: true
  attempt_recovery: true
  rollback_to_known_good: false       # domyślnie NIE — operator decyduje
  max_recovery_attempts: 1            # profil nie eskaluje recovery w nieskończoność
```

## 4. Typy kroków

H0 definiuje typy kroków jako **kontrakty** (w `hive.verification.steps`). Realne
implementacje kroków pojawiają się w H1+.

| Typ | Cel | H0 | H1+ |
|-----|-----|-----|------|
| `adapter_call` | Wywołanie metody adaptera (esp32/rp2040/io/serial/ssh) | interfejs | real |
| `serial_observe` | Obserwacja portu szeregowego do timeoutu lub match | interfejs | real |
| `serial_collect` | Zbieranie logów z portu | interfejs | real |
| `assertion` | Porównanie wartości z oczekiwaniem | interfejs | real |
| `delay` | Czekanie (timeout) | interfejs | real |
| `script` | Wykonanie lokalnego skryptu z env z poprzednich kroków | interfejs | real |
| `parallel` | Równoległe wykonanie pod-kroków | interfejs | real |

## 5. Preconditions

Preconditions muszą być spełnione **przed** rozpoczęciem kroków. Każda precondition
to nazwa lub wyrażenie:

- `device_match_confirmed` — urządzenie w stanie `MATCH_CONFIRMED`
- `device_locked_by_self` — locka trzyma obecny właściciel
- `motor_enable_off` — HIVE-IO potwierdza `MOTOR_ENABLE == OFF`
- `estop_inactive` — E-stop nieaktywny
- `artifact_compatible` — artifact.target == device.target
- `artifact_known_good` — artifact.status == `known-good`

H0 ma wbudowane te preconditions. Rozszerzalność — H1+.

## 6. Wynik weryfikacji

```yaml
result: failed                         # passed | failed | error | skipped
failure_class: serial_boot_timeout    # opis klasyfikacji
expected: boot_signature_within_10s
observed: no_serial_output

steps:
  - id: enter_bootloader
    status: passed
    duration_s: 1.2
  - id: flash_artifact
    status: passed
    duration_s: 8.4
  - id: reset_device
    status: passed
    duration_s: 0.1
  - id: wait_for_serial
    status: failed
    duration_s: 10.0
    observed: no_match

suggested_recovery:
  - power_cycle
  - enter_bootloader
  - reflash_known_good

evidence_bundle_id: eb-2026-07-30-002
duration_s: 19.7
```

`failure_class` jest klasyfikacją błędu (z controlled vocabulary). Klasy są
rozszerzane w kolejnych etapach.

## 7. Egzekucja profilu

```python
from hive.verification.runner import VerificationRunner
from hive.verification.profile import load_profile

profile = load_profile("registry/profiles/esp32-basic-health.yaml")
runner = VerificationRunner(
    device_id="esp32s3-imp2-motor-01",
    artifact_ref="a1b2c3d4-...",
    lock_owner="hare",
    session_id="hive-run-20260730-001",
)
result = runner.run(profile)          # w H0 → NotImplementedError dla I/O kroków
```

W H1+ runner:

- waliduje preconditions,
- wykonuje kroki sekwencyjnie (lub równolegle dla `parallel`),
- zbiera obserwacje,
- klasyfikuje błędy,
- generuje wynik (YAML/JSON),
- opcjonalnie wywołuje recovery.

## 8. Bezpieczeństwo

Profile **nie mogą**:

- wykonywać operacji, które nie są w `hive.adapters` whitelist,
- pomijać locka,
- pomijać `motor_enable_off` dla kroków flash,
- wchodzić w interakcję z GPIO bezpośrednio (tylko przez HIVE-IO).

Profile **muszą**:

- rzucić wyjątkiem, jeśli preconditions nie są spełnione,
- zwrócić `result: error` jeśli wewnętrzny błąd egzekucji (nie mylić z failed),
- zapisać evidence bundle dla każdego wykonania.

## 9. Out-of-scope H0

- Real execution kroków (H1+).
- Recovery automation w profilu (H3+).
- Profile load balancingu / remote execution (H7).
- Profile dla CAN, BLDC, HIL (H6).

H0 dostarcza **model profilu**, **schemat walidacji**, **szkielet runnera**.
Realne wykonanie w H1+ zgodnie z roadmapą.
