# ADR-0003: Device Identity Model

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** Joker + Gaja (gaja-robotics)

## Context

Identyfikacja urządzenia jest krytyczna dla bezpieczeństwa HIVE. Błędna
identyfikacja = potencjalnie flash złego firmware na złym urządzeniu.

Dotychczasowe podejście (z HARE i projektów robotów):

- identyfikacja tylko po `ttyUSB0` / `ttyACM0` — niestabilna,
- identyfikacja tylko po `hostname` / `192.168.x.x` — MITM-vulnerable,
- brak jawnego stanu identyfikacji — operacja albo startuje, albo crashuje.

## Decision

HIVE stosuje **wielocechową identyfikację opartą na kombinacji** + jawny
stan identyfikacji:

**Cechy identyfikacyjne (klasa USB MCU):**
- `usb_vid` (hex, 4 znaki) — wymagane
- `usb_pid` (hex, 4 znaki) — wymagane
- `serial_number` — opcjonalne, ale zalecane
- `stable_path` — opcjonalny alias (udev rule)

**Cechy identyfikacyjne (klasa Linux host):**
- `ssh.host` (IP / hostname) — wskaźnik
- `ssh.host_key_fingerprint` (SHA-256) — autorytet

**Stany identyfikacji** (11 stanów, [`safety-model.md`](../safety-model.md)):
`MATCH_CONFIRMED`, `MATCH_AMBIGUOUS`, `DEVICE_UNKNOWN`, `DEVICE_OFFLINE`,
`DEVICE_BUSY`, `PROJECT_MISMATCH`, `ROLE_MISMATCH`, `FIRMWARE_INCOMPATIBLE`,
`RECOVERY_REQUIRED`, `SAFETY_INTERLOCK_OPEN`, `ESTOP_ACTIVE`.

Tylko `MATCH_CONFIRMED` pozwala na autonomiczne flashowanie. Każdy inny stan
to albo blokada, albo eskalacja.

## Consequences

Positive:
- Eksplicytny stan identyfikacji → audytowalność.
- Kombinacja cech → odporność na pojedynczy błąd.
- Wymuszony fingerprint SSH → ochrona przed MITM.
- Manifest per urządzenie = deklaratywna baza wiedzy.

Negative:
- Więcej pracy przy onboardingu nowego urządzenia (wypełnienie manifestu).
- Manifesty mogą się rozjechać z rzeczywistością → potrzeba regularnego
  audit (H1+).
- Silne wymaganie fingerprintu SSH może utrudniać dev (trzeba pamiętać
  o aktualizacji manifestu po reinstalacji hosta).

## Alternatives considered

- **Tylko VID/PID** — odrzucone: nie rozróżnia dwóch identycznych płytek.
- **Tylko serial** — odrzucone: tanie klony ESP32 nie mają unikalnego serialu.
- **Tylko stable_path** — odrzucone: stable_path może się zmienić między
  sesjami.
- **Brak jawnego stanu identyfikacji** — odrzucone: łamie audyt i debugowanie.
