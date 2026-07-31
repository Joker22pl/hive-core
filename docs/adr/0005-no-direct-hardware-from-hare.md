# ADR-0005: No Direct Hardware Access from HARE

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** Joker + Gaja (gaja-robotics)

## Context

HARE to autonomiczny agent AI, który może popełniać błędy (A1 w threat model).
Jeśli HARE ma bezpośredni dostęp do:

- GPIO,
- przekaźników,
- linii BOOT/RESET,
- `MOTOR_ENABLE`,
- `/dev/tty*`,
- SSH do hostów,

to błąd agenta (np. halucynacja, literówka w device_id, źle wygenerowany
shell command) może:

- flashować złe urządzenie,
- restartować silniki w trakcie testu,
- wywołać recovery w nieskończonej pętli,
- wykonać destrukcyjną komendę na hoście SSH.

To łamie zasadę "fail-safe defaults" i zwiększa ryzyko P0.

## Decision

**HARE NIE MA bezpośredniego dostępu do hardware. Wszystkie operacje przechodzą
przez HIVE Core API.**

HARE ma dostęp do wysokopoziomowego API (zdefiniowanego w
[`architecture.md`](../architecture.md) sekcja 9):

```
identify_device, reserve_device, release_device,
build_artifact, flash_device, deploy_to_linux,
run_verification, collect_evidence,
recover_device, rollback_device, enter_safe_state
```

HARE nie ma endpointów do:
- GPIO bezpośrednio,
- `power_set` / `motor_enable_set` (te są wywoływane wewnętrznie przez HIVE),
- `boot_set` / `reset_pulse` (te są wywoływane wewnętrznie),
- `ssh_exec` na dowolny host (HARE może wywołać `deploy_to_linux` które ma
  dozwolone komendy, ale nie `ssh_exec`),
- `/dev/ttyUSB*` / `/dev/ttyACM*`.

Dodatkowe zabezpieczenia:

- HIVE działa z dedykowanym kontem systemowym (`hive`) z ograniczonymi
  uprawnieniami (sudo tylko dla konkretnych komend, brak shell).
- HIVE NIE akceptuje komend z zewnątrz poza zdefiniowanym API.
- `MOTOR_ENABLE` jest sterowane WYŁĄCZNIE przez HIVE-IO (sprzętowo),
  nawet jeśli HARE poprosi o `motor_enable_set true` → HIVE Core i tak
  deleguje to do HIVE-IO z weryfikacją E-stop.

## Consequences

Positive:
- Defense in depth: błąd HARE nie powoduje bezpośrednio uszkodzenia hardware.
- Audytowalność: każda operacja HARE → evidence bundle w HIVE.
- Testowalność: HARE może być testowany z mock HIVE.
- HIVE może egzekwować safety invariants (np. `MOTOR_ENABLE=OFF` przy flash).

Negative:
- Dodatkowy kod (HIVE Core jako warstwa pośrednia).
- HARE musi być świadomy, że niektóre operacje mogą zostać odmówione.
- Trzeba utrzymywać kontrakt API HIVE.

## Alternatives considered

- **HARE z bezpośrednim hardware access** — odrzucone (patrz context).
- **HARE jako warstwa "safety review" przed HIVE** — odrzucone: nie rozwiązuje
  problemu, bo i tak HARE ma dostęp do hardware. Bezpieczeństwo musi być
  egzekwowane przez ograniczenie dostępu, nie przez review.
- **Whitelist komend SSH** (HARE może wykonać tylko określone komendy) —
  rozważane, ale wybraliśmy pełną separację (HARE nie ma nawet dostępu do SSH,
  tylko `deploy_to_linux` API). Whitelist jest fallback gdyby trzeba było
  dać HARE dostęp SSH w przyszłości.
