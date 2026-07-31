# Recovery Model

> **Źródło prawdy:** [`vision.md`](vision.md) sekcja 16.

## 1. Cel

Recovery to **ostatnia linia obrony** gdy coś poszło nie tak. HIVE ma za zadanie
przywrócić urządzenie do znanego działającego stanu lub — jeśli to niemożliwe —
**zatrzymać się i eskalować do człowieka**.

Recovery NIE jest "kolejną próbą tego samego". Recovery to **sekwencja kroków
zdefiniowana per klasa urządzenia**, która:

- ma **limit prób** (`max_attempts`),
- ma **warunek eskalacji** (po N próbach → człowiek),
- **nie wykonuje się w nieskończonej pętli**,
- **nie ignoruje E-stop**,
- **nie pomija locka**,
- **zbiera evidence** dla każdej próby.

## 2. Klasy urządzeń i strategie recovery

H0 definiuje strategie dla trzech klas z [`vision.md`](vision.md) sekcja 4.

### 2.1 ESP32-S3 (microcontroller)

Strategia: `esp32-bootloader-reflash`

```yaml
id: esp32-bootloader-reflash
description: |
  Wymusza wejście w ROM bootloader (GPIO0 LOW przy RESET), flashuje
  known-good artifact, resetuje, weryfikuje boot signature.

steps:
  - id: power_off
    adapter: io
    method: power_set
    channel: POWER_ESP32_1
    state: false
  - id: set_boot_low
    adapter: io
    method: boot_set
    channel: BOOT_ESP32_1
    state: true
  - id: reset_pulse
    adapter: io
    method: reset_pulse
    channel: RESET_ESP32_1
    duration_ms: 100
  - id: power_on
    adapter: io
    method: power_set
    channel: POWER_ESP32_1
    state: true
  - id: wait_bootloader
    adapter: serial
    method: wait_for_port
    timeout_s: 5
  - id: flash_known_good
    adapter: esp32
    method: flash
    artifact_ref: "{{ device.firmware.known_good_artifact }}"
  - id: release_boot
    adapter: io
    method: boot_set
    channel: BOOT_ESP32_1
    state: false
  - id: reset_pulse_final
    adapter: io
    method: reset_pulse
    channel: RESET_ESP32_1
    duration_ms: 100
  - id: verify_boot
    adapter: serial
    method: assert_signature
    expected: "ESP-ROM:esp32s3"
    timeout_s: 10

success:
  next_action: report_pass

failure:
  attempt_recovery: false               # nie rekurencyjnie
  escalate_to_human: true
```

### 2.2 RP2040 (microcontroller)

Strategia: `rp2040-bootsel-reflash`

```yaml
id: rp2040-bootsel-reflash
description: |
  Wymusza BOOTSEL (recovery przez RP2040 bootloader), flashuje UF2 z
  known-good artifact, resetuje, weryfikuje boot.

steps:
  - id: hold_bootsel
    adapter: io
    method: boot_set
    channel: BOOT_PICO_1
    state: true
  - id: power_off_then_on
    adapter: io
    method: power_cycle
    channel: POWER_PICO_1
    off_duration_ms: 200
  - id: wait_mass_storage
    adapter: usb
    method: wait_for_drive
    expected_label: "RPI-RP2"
    timeout_s: 5
  - id: copy_uf2
    adapter: rp2040
    method: copy_uf2
    artifact_ref: "{{ device.firmware.known_good_artifact }}"
  - id: release_bootsel
    adapter: io
    method: boot_set
    channel: BOOT_PICO_1
    state: false
  - id: wait_serial
    adapter: serial
    method: wait_for_port
    timeout_s: 10
  - id: verify_boot
    adapter: serial
    method: assert_signature
    expected: "RP2040"
    timeout_s: 5

success:
  next_action: report_pass

failure:
  attempt_recovery: false
  escalate_to_human: true
```

### 2.3 Linux host (SSH)

Strategia: `linux-ssh-service-restart`

```yaml
id: linux-ssh-service-restart
description: |
  Próbuje przywrócić host do stanu operacyjnego: restartuje zawieszone
  usługi, rollbackuje ostatni deploy, lub — w ostateczności — eskaluje.

steps:
  - id: ssh_ping
    adapter: ssh
    method: exec
    command: "true"
    timeout_s: 5
  - id: check_services
    adapter: ssh
    method: exec
    command: "systemctl is-system-running"
  - id: rollback_last_deploy
    adapter: ssh
    method: exec
    command: "/opt/<project>/rollback.sh"
    on_failure: continue
  - id: restart_services
    adapter: ssh
    method: exec
    command: "systemctl restart <service>.service"
    on_failure: escalate

success:
  next_action: report_pass

failure:
  attempt_recovery: false
  escalate_to_human: true
```

### 2.4 Host Linux niedostępny przez SSH

Strategia: `linux-host-power-cycle`

```yaml
id: linux-host-power-cycle
description: |
  Gdy host nie odpowiada na SSH, próbuje power cycle przez PDU / smart plug
  podłączony do HIVE-IO. Wymaga `power_control_allowed: true` w manifeście.

steps:
  - id: power_off
    adapter: io
    method: power_set
    channel: POWER_HOST_1
    state: false
  - id: wait_off
    adapter: io
    method: delay
    duration_s: 5
  - id: power_on
    adapter: io
    method: power_set
    channel: POWER_HOST_1
    state: true
  - id: wait_ssh
    adapter: ssh
    method: wait_for_connect
    timeout_s: 60
  - id: verify
    adapter: ssh
    method: exec
    command: "systemctl is-system-running"

success:
  next_action: report_pass

failure:
  attempt_recovery: false
  escalate_to_human: true
```

## 3. Limity i eskalacja

Każde wywołanie recovery ma:

- `max_attempts` (z manifestu urządzenia, domyślnie 3),
- `escalate_to_human_after` (zwykle = `max_attempts`),
- `attempt_id` inkrementowany przy każdej próbie,
- `evidence_bundle_id` zapisywany per próba.

Gdy `attempt_id > max_attempts`:

- recovery przerywa się,
- generowany jest `ESCALATION` event w evidence bundle,
- HIVE Core zwraca `RECOVERY_FAILED` + `escalation_required: true`,
- HARE (lub operator) decyduje, co dalej (zwykle: ręczna interwencja).

## 4. Klasy błędów

H0 definiuje słownik klas błędów:

- `SERIAL_PORT_LOST`
- `BOOTLOADER_TIMEOUT`
- `FLASH_VERIFY_FAILED`
- `BOOT_SIGNATURE_TIMEOUT`
- `MICROROS_AGENT_MISSING`
- `SSH_CONNECT_TIMEOUT`
- `SSH_HOST_KEY_MISMATCH`
- `HOST_UNREACHABLE`
- `SERVICE_RESTART_FAILED`
- `CONTROL_LINK_LOST`          # HIVE-IO heartbeat
- `LOCK_ACQUIRE_FAILED`
- `PRECONDITION_FAILED`
- `UNKNOWN`

Każda klasa ma `suggested_recovery_strategy` (np. `SERIAL_PORT_LOST` →
`linux-host-power-cycle`).

## 5. Bezpieczeństwo recovery

Recovery **NIE WOLNO**:

- ignorować E-stop (nawet jeśli strategia nie wspomina o E-stop; check jest
  automatyczny w runnerze),
- pomijać locka (lock musi być utrzymany przez całą sekwencję),
- flashować czegoś innego niż `known_good_artifact` (chyba że strategia
  wyraźnie mówi inaczej),
- działać bez evidence bundle (każda próba = bundle),
- wchodzić w rekurencję (recovery nie woła recovery).

## 6. Out-of-scope H0

- Real execution strategii (H3+).
- Profile-specific recovery (np. BLDC recovery z enkoderów — H6).
- Custom strategies per project (H3+).
- Auto-rollback po każdym niepowodzeniu (H3+, z osobnym enable flag).

H0 dostarcza **szkielet strategii** i **interfejs runnera**. Implementacja
w H3+ razem z realnym I/O.
