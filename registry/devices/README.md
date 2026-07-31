# Device Registry

Katalog `registry/devices/` zawiera manifesty poszczególnych urządzeń
w formacie YAML, zgodne ze [`../schemas/device.schema.json`](../schemas/device.schema.json).

## H0 przykłady

- `esp32s3-imp2-motor-01.yaml` — IMP2 motor controller (ESP32-S3 Pico)
- `esp32s3-imp2-sensor-01.yaml` — IMP2 sensor controller (ESP32-S3 Pico)
- `pico-test-01.yaml` — RP2040 dev board używana jako test target
- `imp2-ros2-nuc.yaml` — host Linux (NUC) z ROS 2
- `hive-io-controller.yaml` — HIVE-IO (osobny Pico, kontroler stanowiska)

Wszystkie są w pełni zgodne ze schematem (zweryfikowane testami).

## Konwencja nazewnictwa

`<typ>-<projekt>-<rola>-<numer>`, np.:

- `esp32s3-imp2-motor-01`
- `rp2040-test-target-01`
- `nuc-imp2-ros2-01`
- `hive-io-controller`

Przy wielu identycznych płytkach: sufiks `-NN` (zero-padded do 2+ cyfr).

## Walidacja

Każdy manifest jest walidowany przez `hive.registry.validate_manifest()`.
Nieprawidłowy manifest → wyjątek, urządzenie nie może brać udziału w
operacjach HIVE do czasu naprawy.

## Zarządzanie

H0: ręczne (pliki YAML, wersjonowane w git).
H1+: CLI `hive device register`, `hive device inspect`, przechowywanie w
SQLite + migracje.
