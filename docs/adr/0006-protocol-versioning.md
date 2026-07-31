# ADR-0006: Protocol Versioning (HIVE Core ↔ HIVE-IO)

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** Joker + Gaja (gaja-robotics)

## Context

Komunikacja HIVE Core ↔ HIVE-IO musi ewoluować w czasie (nowe komendy,
nowe kanały, nowe zabezpieczenia). Bez jasnego wersjonowania:

- stary HIVE Core + nowy HIVE-IO firmware → niekompatybilność cicha,
- nowy HIVE Core + stary HIVE-IO firmware → ciche pomijanie komend,
- mix wielu kontrolerów HIVE-IO w jednym systemie → jeszcze gorzej.

## Decision

Protokół HIVE Core ↔ HIVE-IO jest **wersjonowany semantycznie**.

**Pole:** `protocol_version` (string) w każdej wiadomości.
**Format:** SemVer `"MAJOR.MINOR.PATCH"`.

**Aktualna wersja:** `"0.1.0"` (H0).

**Semantyka:**

- `MAJOR` (zmiana): niekompatybilna zmiana protokołu. Stary klient odrzuca
  wiadomości z innym MAJOR. HIVE-IO musi wspierać poprzedni MAJOR przez
  co najmniej jeden release cycle.
- `MINOR` (zmiana): dodanie nowej komendy lub pola. Stary klient ignoruje
  nieznane pola (forward compatibility). Nowy klient akceptuje brak
  nowych pól (backward compatibility).
- `PATCH` (zmiana): bugfix, refaktor, brak zmiany w wiadomościach.

**Discovery:**

- Klient (HIVE Core) na starcie wysyła `get_capabilities`.
- HIVE-IO odpowiada z `protocol_version` + listą obsługiwanych komend
  + listą dostępnych kanałów.
- Klient porównuje MAJOR — jeśli nie pasuje → błąd krytyczny, bezpieczny stop.

**Negocjacja MINOR:**

- Klient może żądać minimalnej wersji (np. `"0.2.0"`) w requestach
  (opcjonalnie, H2+).

**Kompatybilność wstecz:**

- HIVE-IO firmware MUSI wspierać poprzedni MAJOR, jeśli jest jedynym
  kontrolerem w systemie (grace period: 6 miesięcy).
- HIVE Core może wspierać wiele MAJOR jednocześnie (polyglot), ale
  domyślnie używa najnowszego.

## Consequences

Positive:
- Jasna komunikacja o wersji w każdej wiadomości.
- Świadome decyzje o breaking changes.
- Możliwość ewolucji protokołu bez lockstep deployment.

Negative:
- Trzeba utrzymywać dokument wersji (`docs/io-protocol-changelog.md`,
  planowane H2+).
- Testowanie wielu wersji jednocześnie (H2+).
- Dodatkowe pole w każdej wiadomości (minimalny narzut).

## Alternatives considered

- **Brak wersjonowania** — odrzucone: każda zmiana protokołu to ryzyko
  cichej niekompatybilności.
- **Date-based versioning (`2026-07-30`)** — odrzucone: mniej porównywalne;
  SemVer jest standardem.
- **Wersjonowanie per komenda** (każda komenda ma wersję) — rozważane,
  ale za dużo narzutu; lepiej wersjonować protokół jako całość + lista
  capabilities.
- **Wersjonowanie przez URL/endpoint** — nie dotyczy (to nie HTTP).

## Notes

- Planowane przyszłe rozszerzenia (H5+): CRC, format binarny, HMAC
  autoryzacja. Każde z tych rozszerzeń będzie nowym MINOR (np. `0.2.0`).
- Wielokontrolerowość (H5+) doda `controller_id` do wiadomości (MINOR).
- Komunikacja sieciowa przez HIVE Gateway (H7) będzie nowym MAJOR
  (np. `1.0.0`) — bo zmienia się transport.

## See also

- [`../io-protocol.md`](../io-protocol.md) — pełna specyfikacja protokołu
- [`ADR-0004`](0004-io-controller-as-separate-pico.md) — HIVE-IO jako osobny Pico
