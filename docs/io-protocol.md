# HIVE Core ↔ HIVE-IO Protocol (MVP)

> **Status:** specyfikacja (H0). Implementacja firmware — [`hive-io`](../hive-io/).
> Implementacja klienta — `hive.io_controller.client.HiveIOClient` (szkielet w H0).

## 1. Transport

- **Medium:** USB
- **Klasa urządzenia:** USB CDC (Communications Device Class)
- **Encoding:** UTF-8
- **Framing:** JSON Lines (jeden JSON na linię, terminator `\n` / `0x0A`)
- **Prędkość:** nie dotyczy (USB CDC emuluje serial, baud rate ustawiony na
  dowolny — np. 115200 — dla kompatybilności)

## 2. Wersjonowanie

Każda wiadomość ma pole `protocol_version`. Obecna wersja: `"0.1.0"`.

Klient (HIVE Core) odrzuca wiadomości z nieobsługiwaną wersją protokołu.
HIVE-IO raportuje `protocol_version` w odpowiedzi na `get_capabilities`.

## 3. Typy wiadomości

### 3.1 Request (HIVE Core → HIVE-IO)

```json
{
  "protocol_version": "0.1.0",
  "request_id": "req-001",
  "command": "power_set",
  "params": {
    "channel": "esp32_1",
    "state": true
  }
}
```

### 3.2 Response (HIVE-IO → HIVE Core)

```json
{
  "protocol_version": "0.1.0",
  "request_id": "req-001",
  "result": "ok",
  "observed_state": true,
  "details": null
}
```

### 3.3 Error response

```json
{
  "protocol_version": "0.1.0",
  "request_id": "req-001",
  "result": "error",
  "error_class": "SAFETY_INTERLOCK_OPEN",
  "message": "Cannot power on while ESTOP active",
  "observed_state": null
}
```

### 3.4 Async event (HIVE-IO → HIVE Core, unsolicited)

```json
{
  "protocol_version": "0.1.0",
  "event_id": "evt-42",
  "event": "ESTOP_PRESSED",
  "timestamp": "2026-07-30T04:00:00.123Z",
  "details": {
    "estop_id": "ESTOP_FRONT"
  }
}
```

## 4. Komendy MVP

| Command | Params | Result | Opis |
|---------|--------|--------|------|
| `get_status` | — | `ok` z `observed_state: status_report` | Zwraca pełny raport stanu |
| `get_capabilities` | — | `ok` z capabilities | Wersja FW, kanały, limity |
| `heartbeat` | — | `ok` z `observed_state: ack` | Klient utrzymuje heartbeat |
| `safe_state` | — | `ok` | Wymusza stan bezpieczny (MOTOR_ENABLE=OFF, itp.) |
| `power_set` | `{channel, state}` | `ok` z `observed_state: bool` | Włącza/wyłącza kanał zasilania |
| `power_cycle` | `{channel, off_duration_ms}` | `ok` | Power off → wait → power on |
| `reset_pulse` | `{channel, duration_ms}` | `ok` | Impuls RESET (active LOW) |
| `boot_set` | `{channel, state}` | `ok` | Wystawia/zeruje linię BOOT |
| `motor_enable_set` | `{state}` | `ok` z `observed_state: bool` | Master enable silników |
| `estop_status` | — | `ok` z `observed_state: ACTIVE \| INACTIVE` | Status E-stop |
| `firmware_version` | — | `ok` z wersją | Wersja firmware HIVE-IO |
| `reset_io_controller` | — | `ok` | Restart HIVE-IO (do użytku serwisowego) |

## 5. Kanały (kanały logiczne, nazwy konwencjonalne)

| Kanał | Kierunek | Default | Opis |
|-------|----------|---------|------|
| `POWER_ESP32_1` | out | OFF | Zasilanie ESP32 #1 (np. motor controller) |
| `POWER_ESP32_2` | out | OFF | Zasilanie ESP32 #2 (np. sensor controller) |
| `POWER_PICO_1` | out | OFF | Zasilanie RP2040 test target |
| `POWER_PICO_2` | out | OFF | Zasilanie RP2040 (rezerwowy) |
| `POWER_SENSOR_1` | out | OFF | Zasilanie czujnika |
| `POWER_AUX_1` | out | OFF | Zasilanie pomocnicze |
| `POWER_HOST_1` | out | OFF | Zasilanie hosta (przez PDU/smart plug) |
| `RESET_ESP32_1` | out | RELEASED | Linia RESET dla ESP32 #1 |
| `RESET_ESP32_2` | out | RELEASED | Linia RESET dla ESP32 #2 |
| `RESET_PICO_1` | out | RELEASED | Linia RESET dla RP2040 |
| `BOOT_ESP32_1` | out | INACTIVE | Linia BOOT dla ESP32 #1 |
| `BOOT_ESP32_2` | out | INACTIVE | Linia BOOT dla ESP32 #2 |
| `BOOT_PICO_1` | out | INACTIVE | Linia BOOT dla RP2040 |
| `MOTOR_ENABLE` | out | OFF | Master enable silników |
| `ESTOP_SENSE` | in | — | Wejście E-stop (fizyczny sygnał) |

HIVE-IO **musi** raportować rzeczywisty stan kanału (`observed_state`) po każdej
zmianie. Klient HIVE Core używa `observed_state` jako źródła prawdy (nie
pamięci, co "wysłał").

## 6. Heartbeat i kontrola linku

- Klient wysyła `heartbeat` co **200 ms** (zalecane; konfigurowalne).
- HIVE-IO ma **wewnętrzny watchdog** — jeśli nie dostanie heartbeat przez
  **timeout** (H0 default: 1 s), wymusza `safe_state()`.
- Po powrocie heartbeat HIVE-IO wysyła async event `CONTROL_LINK_RESTORED`.
- Klient HIVE Core ma **własny watchdog** — jeśli HIVE-IO nie odpowiada przez
  **timeout**, klient loguje `CONTROL_LINK_LOST` i przerywa bieżącą operację.

## 7. Bezpieczeństwo

- **E-stop priorytet:** `power_set`, `motor_enable_set`, `reset_pulse`, `boot_set`
  są odrzucane, jeśli `ESTOP_SENSE == ACTIVE`. Wyjątek: `safe_state` jest zawsze
  dozwolony (i sam natychmiast wymusza bezpieczny stan).
- **`safe_state` idempotentny:** wielokrotne wywołanie nie zmienia stanu.
- **Boot mode lockout:** `boot_set true` na kanale BOOT_* wymaga uprzedniego
  `power_off` na odpowiednim POWER_* kanale (zapobiega przypadkowemu wejściu
  w tryb boot podczas pracy).
- **Timeout per komendę:** klient HIVE Core wymusza timeout (domyślnie 5 s)
  na każdą komendę. Brak odpowiedzi → retry raz → eskalacja.

## 8. Rozszerzenia przyszłe (planned, not H0)

- **CRC na linii:** tryb binarny z CRC32 dla komend wymagających niskiego
  narzutu; JSON Lines pozostaje fallbackiem.
- **Format binarny:** dla szybkich kanałów (np. 100 Hz PWM via IO).
- **Uwierzytelnianie:** HMAC podpisany kluczem z HIVE Core (H5+).
- **Wiele kontrolerów:** `controller_id` w wiadomości (H5+).
- **Komunikacja sieciowa:** gateway mode (H7) — przez Raspberry Pi 1 jako
  HIVE Gateway udostępniający UART/USB/programatory przez sieć.
- **Telemetria:** HIVE-IO publikuje pomiary (napięcia, prądy, temperatury)
  w eventach (H6+).

## 9. Przykładowa sekwencja flash ESP32

```jsonc
// 1. Sprawdź E-stop
{"request_id":"r1","command":"estop_status"}
// → {"request_id":"r1","result":"ok","observed_state":"INACTIVE"}

// 2. Wyłącz silniki (idempotent)
{"request_id":"r2","command":"motor_enable_set","params":{"state":false}}
// → {"request_id":"r2","result":"ok","observed_state":false}

// 3. Wyłącz zasilanie ESP32
{"request_id":"r3","command":"power_set","params":{"channel":"esp32_1","state":false}}
// → {"request_id":"r3","result":"ok","observed_state":false}

// 4. Ustaw BOOT low (tryb bootloader)
{"request_id":"r4","command":"boot_set","params":{"channel":"boot_esp32_1","state":true}}
// → {"request_id":"r4","result":"ok","observed_state":true}

// 5. Krótki reset
{"request_id":"r5","command":"reset_pulse","params":{"channel":"reset_esp32_1","duration_ms":100}}
// → {"request_id":"r5","result":"ok","observed_state":true}

// 6. Włącz zasilanie (boot w ROM bootloader)
{"request_id":"r6","command":"power_set","params":{"channel":"esp32_1","state":true}}
// → {"request_id":"r6","result":"ok","observed_state":true}

// 7. [zewnętrznie] esptool flashuje przez USB

// 8. Zwolnij BOOT
{"request_id":"r7","command":"boot_set","params":{"channel":"boot_esp32_1","state":false}}
// → {"request_id":"r7","result":"ok","observed_state":false}

// 9. Reset do app
{"request_id":"r8","command":"reset_pulse","params":{"channel":"reset_esp32_1","duration_ms":100}}
// → {"request_id":"r8","result":"ok","observed_state":true}

// 10. Status
{"request_id":"r9","command":"get_status"}
// → {"request_id":"r9","result":"ok","observed_state":{"power_esp32_1":true,"motor_enable":false,...}}
```

## 10. Out-of-scope H0

- Real USB CDC client (H2).
- Real firmware HIVE-IO (H2).
- CRC, HMAC, format binarny (H5+).
- Multi-controller (H5+).

H0 dostarcza **kontrakt protokołu**, **konwencję kanałów**, **przykładową
sekwencję** i **szkielet klienta** (model + walidacja, bez realnego USB I/O).

## 11. ESTOP injection — test-only mechanism

**Decision (ADR-0006 follow-up, 2026-07-30):** estop_inject is **not**
a production wire-protocol command. It existed in early H0 drafts but
three concerns led to its removal:

1. ESTOP is **physical** — the state is owned by the firmware reading a
   GPIO pin. HIVE Core has no business setting it via the wire.
2. Production code could mistakenly rely on ESTOP injection as a
   "shortcut" rather than reading the real estop_status.
3. Mixing test hooks onto the wire protocol confuses the contract
   documentation and creates a false sense of parity between Core and
   IO.

Therefore:

* The **production wire** has no estop_inject command. The mock
  HIVE-IO dispatcher returns UNKNOWN_COMMAND for it (verified by
  test_mock_unknown_command_returns_error).
* Tests interact with the ESTOP state via a **separate** test-hook
  surface: :class:\ obtained
  from :func:\. This is
  deliberately not part of the public HiveIOClient API — production
  code cannot discover it.
* The mock's ESTOP state is still consulted by motor_enable_set and
  power_set so the safety contract is testable end-to-end.

The corresponding wire assertion is exercised by
tests/unit/test_io_controller.py::test_mock_unknown_command_returns_error
and the test-hook separation is locked in by
tests/unit/test_mock_hooks.py.

