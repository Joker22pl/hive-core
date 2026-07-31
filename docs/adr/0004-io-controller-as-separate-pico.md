# ADR-0004: IO Controller as Separate Pico (HIVE-IO)

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** Joker + Gaja (gaja-robotics)

## Context

HIVE potrzebuje fizycznego sterowania:

- zasilaniem (kanały on/off + power cycle),
- liniami RESET,
- liniami BOOT,
- `MOTOR_ENABLE`,
- E-stop sense.

Rozważane opcje:

1. **HIVE Core steruje bezpośrednio przez GPIO** (np. z NUC) — wymaga NUC z GPIO
   (nie ma) lub dodatkowej karty GPIO.
2. **HIVE Core steruje przez USB relay board** (gotowy moduł) — komercyjne
   urządzenia istnieją, ale są drogie i mają zamknięte API.
3. **Osobny mikrokontroler (RPi Pico) z własnym firmware** — pełna kontrola,
   niski koszt, łatwe do modyfikacji.
4. **Oprogramowanie na docelowym MCU** — nie, MCU jest targetem testowym,
   nie kontrolerem stanowiska.

## Decision

**HIVE-IO = osobny RPi Pico z dedykowanym firmware (C/C++, Pico SDK, USB CDC).**

Komunikacja HIVE Core ↔ HIVE-IO: **USB CDC + JSON Lines**.

HIVE-IO NIE JEST urządzeniem testowym — to **kontroler stanowiska**.

Docelowy układ stanowiska:
```
RPi Pico A (HIVE-IO)  ← stały kontroler, USB do NUC
RPi Pico B            ← urządzenie rozwojowe i testowe
ESP32-S3 (target)     ← urządzenie testowane
```

HIVE-IO:
- ma własny watchdog + heartbeat,
- startuje w `safe_state`,
- utrzymuje `MOTOR_ENABLE=OFF` przy utracie heartbeat,
- ma wyższy priorytet dla E-stop niż HIVE Core.

## Consequences

Positive:
- Pełna kontrola nad protokołem (JSON Lines, wersjonowany).
- Niezależność HIVE-IO od HIVE Core (fail-safe default).
- Pico jest tani (~10 EUR), łatwy do wymiany.
- Firmware można aktualizować i testować niezależnie.
- Jasna granica odpowiedzialności (HIVE-IO = hardware safety; HIVE Core =
  orkiestracja).

Negative:
- Dodatkowy mikrokontroler do utrzymania.
- Dodatkowy firmware do debugowania.
- Dodatkowy kabel USB.
- Więcej płytek do zaprojektowania (HIVE-IO carrier board w H2+).

## Alternatives considered

- **USB relay board (komercyjny)** — odrzucone: zamknięte API, drogie,
  brak fail-safe semantics.
- **HIVE Core na NUC + karta GPIO przez PCIe/USB** — odrzucone: NUC nie
  ma GPIO, karty GPIO wymagają dodatkowych driverów; brak fail-safe
  defaults.
- **Wszystko na jednym ESP32-S3** — odrzucone: target = kontroler = ten
  sam układ → błąd w targetu = utrata kontrolera. Niedopuszczalne.
- **Raspberry Pi 1 jako kontroler** — odrzucone: RPi 1 ma Linux, jest
  ciężki jak kontroler hardware; za dużo warstw między GPIO a HIVE Core.
  Planowane jako HIVE Gateway w H7+.

## Notes

- HIVE-IO firmware żyje w osobnym repo `hive-io`.
- MVP HIVE-IO (H2) to firmware na dev board (Pico), bez dedykowanej
  płytki carrier. Carrier board planowany po walidacji MVP.
