# Device Identity Model

> **Źródło prawdy:** [`vision.md`](vision.md) sekcja 7 i 8 oraz schema
> [`../schemas/device.schema.json`](../schemas/device.schema.json).

## 1. Filozofia

Identyfikacja urządzenia opiera się na **kombinacji cech** i **rejestrze manifestów**.
Nigdy nie opieramy się na pojedynczej cesze takiej jak `/dev/ttyUSB0` albo
adres IP — te rzeczy są niestabilne i mogą się zmieniać między sesjami.

Manifest urządzenia w `registry/devices/` jest **deklaratywnym opisem** tego,
czego HIVE ma oczekiwać. Runtime discovery **weryfikuje** zgodność z manifestem
i zwraca `IdentificationStatus`.

## 2. Klasy urządzeń (H0)

W H0 rozróżniamy trzy klasy, zgodnie z [`vision.md`](vision.md) sekcja 4:

| Klasa | Typ manifestu | Klucz identyfikacyjny |
|-------|---------------|------------------------|
| USB MCU | `microcontroller` | VID + PID + serial (jeśli dostępny) |
| Serial MCU (z BOOT) | `microcontroller` | VID + PID + serial + tryb (NORMAL/BOOT) |
| Host Linux (SSH) | `linux_host` | fingerprint klucza SSH + adres (IP/hostname) |
| HIVE-IO controller | `io_controller` | VID + PID + serial + protokół wersja |

Planowane na H1+:

- CAN devices (np. PEAK PCAN-USB),
- programatory (np. ST-Link, J-Link),
- debuggery (np. OpenOCD).

## 3. Manifest urządzenia — minimalne pola

```yaml
device_id: esp32s3-imp2-motor-01           # unikalne w ramach HIVE
display_name: IMP2 motor controller       # czytelna nazwa
type: microcontroller                      # microcontroller | linux_host | io_controller
board: esp32-s3-pico                      # konkretna płytka
project: IMP2                              # projekt, do którego urządzenie należy
role: motor-controller                     # rola w projekcie

identity:
  usb_vid: "303A"                          # hex string, 4 znaki
  usb_pid: "1001"                          # hex string, 4 znaki
  serial_number: null                      # null = nie wymagane; wypełnij po odkryciu
  stable_path: null                        # opcjonalny alias, np. /dev/hive/imp2-motor-controller

capabilities:
  - usb-cdc
  - uart
  - flash
  - reset
  - boot-control
  - microros-serial

firmware:
  target: esp32s3
  expected_project: motor-controller
  known_good_artifact: null               # referencja do artifact_id; null = brak fallbacku

safety:
  motor_power_required: false
  motor_enable_must_be_off_during_flash: true
  automatic_power_cycle_allowed: true
  automatic_flash_allowed: true            # false = wymaga ręcznej zgody na każdy flash

recovery:
  strategy: esp32-bootloader-reflash       # patrz hive.recovery.registry
  max_attempts: 3
  escalate_to_human_after: 3
```

Pełna walidacja przez `device.schema.json`.

## 4. Stabilna identyfikacja — sekwencja

```
1. Skanowanie fizyczne:
   - USB: VID, PID, serial, port (np. /dev/ttyACM0)
   - SSH: adres, fingerprint klucza serwera

2. Dopasowanie do rejestru:
   - szukaj manifestu, który ma pasujący (VID + PID + serial)
   - jeśli >1 manifest pasuje → MATCH_AMBIGUOUS
   - jeśli 0 manifestów pasuje → DEVICE_UNKNOWN (dodaj do rejestru przed flashem)

3. Weryfikacja roli i projektu:
   - jeśli urządzenie przypisane do innego projektu → PROJECT_MISMATCH
   - jeśli urządzenie ma inny role niż oczekiwany → ROLE_MISMATCH

4. Weryfikacja firmware:
   - jeśli artefakt ma target != device.firmware.target → FIRMWARE_INCOMPATIBLE

5. Jeśli wszystko OK → MATCH_CONFIRMED
```

## 5. Serial number — ujawnianie

Niektóre urządzenia (np. tanie klony ESP32) nie mają unikalnego serialu.
Manifest może mieć `serial_number: null` — wtedy identyfikacja opiera się tylko
na (VID, PID) i `stable_path`. To jest mniej bezpieczne niż serial, dlatego
`MATCH_CONFIRMED` wymaga:

- serial niepusty → identyfikacja mocna,
- serial pusty, ale `stable_path` istnieje i jest spójny → identyfikacja średnia,
- brak obu → identyfikacja słaba; **HIVE domyślnie odmawia flashowania**.

Operator może nadpisać zachowanie przez `safety.automatic_flash_allowed: false`
w manifeście (co i tak wymaga ręcznej zgody per flash).

## 6. `stable_path` — alias

`stable_path` (np. `/dev/hive/imp2-motor-controller`) jest aliasem utrzymywanym
przez `hive.discovery`. Może to być:

- dowiązanie symboliczne tworzone przez regułę udev (zalecane),
- zarejestrowana ścieżka w HIVE (gdy udev nie jest dostępny).

`stable_path` NIE zastępuje identyfikacji VID/PID/serial — jest ułatwieniem.

## 7. SSH fingerprint

Dla hostów Linux identyfikacja opiera się na:

- `host` (IP lub hostname) — tylko jako wskaźnik, nie autorytet,
- `ssh_host_key_fingerprint` (SHA-256) — autorytet.

Każdy host ma manifest w `registry/hosts/` z kluczem:

```yaml
device_id: imp2-ros2-nuc
type: linux_host
ssh:
  host: 192.168.1.184
  port: 22
  user: kotekrobot
  host_key_fingerprint: "SHA256:abcd..."   # wymagane
  known_host_entry: null                    # opcjonalne, dla wygody
```

HIVE **odmawia** połączenia, jeśli fingerprint nie zgadza się z manifestem
(ochrona przed MITM). Pierwsze połączenie z nieznanym hostem → `DEVICE_UNKNOWN` +
wymaga jawnej akceptacji operatora (H1+).

## 8. HIVE-IO — osobna ścieżka

HIVE-IO jest identyfikowane osobno. Ma własny manifest w `registry/devices/`
oraz dedykowany wpis w modelu bezpieczeństwa. Komunikacja z HIVE-IO odbywa się
przez klienta `hive.io_controller`, który:

- egzekwuje wersję protokołu (`protocol_version`),
- nigdy nie używa HIVE-IO do flashowania (to osobna rola; HIVE-IO = kontroler
  stanowiska, nie target),
- w H0 wysyła komendy przez mock (szkielet); real USB-CDC client w H2.

## 9. Walidacja schematu

Wszystkie manifesty są walidowane przez `device.schema.json` (i odpowiedniki dla
artefaktów, profili, evidence). Walidacja jest częścią `hive.registry.validate_manifest()`.
Nieprawidłowy manifest → wyjątek + brak operacji sprzętowej na tym urządzeniu.

## 10. Out-of-scope H0

- Real USB discovery (H1).
- Real SSH connection i fingerprint verification (H4).
- Udev rule installer (H1).
- Multi-host discovery scan (H1).

H0 dostarcza model danych, schemat i walidator. Real I/O pojawia się w kolejnych
etapach.
