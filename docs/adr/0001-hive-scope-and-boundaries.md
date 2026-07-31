# ADR-0001: HIVE Scope and Boundaries

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** Joker (Lucas) + Gaja (gaja-robotics)

## Context

HIVE (Hermes Integration & Verification Environment) jest wprowadzany jako trzeci
współgracz w ekosystemie projektów robotycznych Jokera, obok HARE (agent
inżynierski) i HEOS (zasady). Potrzebna jest jasna granica odpowiedzialności,
żeby:

- HARE nie wykonywał niekontrolowanych operacji na sprzęcie,
- HIVE nie podejmował decyzji inżynierskich,
- HEOS był źródłem prawdy dla zasad ogólnych.

## Decision

HIVE jest **kontrolowanym środowiskiem sprzętowo-programowym** udostępniającym:

- wykrywanie i jednoznaczną identyfikację urządzeń,
- rezerwację zasobów,
- budowanie artefaktów i flashowanie,
- wykonywanie profili weryfikacyjnych,
- recovery i rollback,
- evidence bundles,
- sterowanie kontrolerem stanowiska HIVE-IO (osobne Pico).

HIVE **nie jest**:

- agentem AI / orkiestratorem (to HARE),
- bazą danych ogólnego przeznaczenia (to hermes-registry),
- dashboardem (to HCC/HDS),
- frameworkiem ROS 2 (to projekty robotów).

Granica HARE ↔ HIVE: **HARE decyduje co/kiedy; HIVE wykonuje jak/na czym**.
HARE ma dostęp do wysokopoziomowego API HIVE; nie ma dostępu do surowych
GPIO, przekaźników, BOOT/RESET, `/dev/tty*`, ani bezpośredniego SSH.

## Consequences

Positive:
- Jasna odpowiedzialność → łatwiejsze audyt i debugowanie.
- HARE może być testowany z mock HIVE (bez hardware).
- HIVE może być rozwijane niezależnie od HARE.
- Kontroler stanowiska (HIVE-IO) oddzielony od logiki (HIVE Core) =
  fail-safe defaults.

Negative:
- Dodatkowa warstwa abstrakcji → więcej kodu do utrzymania.
- HARE+HIVE musi być rozwijane koherentnie (kontrakt API jest wspólny).

## Alternatives considered

- **HARE z wbudowanym hardware access** (bez HIVE) — odrzucone: zbyt
  ryzykowne (AI agent dotyka hardware bezpośrednio); utrudnia testowanie.
- **HIVE jako część HARE** (jeden monolityczny agent) — odrzucone: łamie
  separation of concerns; utrudnia niezależne rozwijanie.
- **HIVE jako klient OpenOCD / esptool bez abstrakcji** — odrzucone:
  nie rozwiązuje problemu identyfikacji i lockingu; tylko cienka warstwa
  na istniejące narzędzia.
