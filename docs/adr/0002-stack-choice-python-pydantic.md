# ADR-0002: Stack Choice — Python 3.12 + Pydantic v2

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** Joker + Gaja (gaja-robotics)

## Context

HIVE Core potrzebuje:

- bogatej walidacji modeli danych (device, artifact, profile, evidence),
- dobrej obsługi YAML/JSON dla manifestów,
- dobrej integracji z istniejącymi bibliotekami (`pyudev`, `pyserial`,
  `paramiko`, `esptool`),
- łatwego testowania i szybkiej iteracji.

## Decision

**HIVE Core = Python 3.12 + Pydantic v2.**

Biblioteki wybrane:
- `pydantic>=2.6` — modele + walidacja
- `PyYAML>=6.0` — manifesty YAML
- `jsonschema>=4.21` — walidacja zewnętrznych JSON Schema
- `typer>=0.12` + `rich>=13.7` — CLI
- `python-json-logger>=2.0` — structured logging
- `pytest>=8.0` + `pytest-cov` + `ruff` — testy + lint
- Opcjonalne (instalowane per use case): `paramiko`, `pyudev`, `pyserial`,
  `esptool`

## Consequences

Positive:
- Python 3.12 ma dobre wsparcie `match`/`case`, `Self`, performance.
- Pydantic v2 (Rust core) jest szybszy i ma lepszą walidację niż v1.
- `pyudev`, `pyserial`, `paramiko`, `esptool` są dojrzałe i aktywnie
  rozwijane.
- Łatwe testowanie z mockami.
- Szybka iteracja — brak kompilacji.

Negative:
- Dynamic typing → trzeba pilnować typów (Pydantic + mypy pomagają).
- Wydajność gorsza niż Rust/C++ (akceptowalna dla HIVE; tu nie ma hot path).
- Zależności trzeba lockować (`pip-tools`, `requirements.lock`).

## Alternatives considered

- **Rust + tokio** — odrzucone: overkill dla projektu hobbystycznego;
  wolniejsza iteracja; brak naturalnych bindingów do istniejących narzędzi.
- **Go** — odrzucone: brak `pyudev`/`pyserial` equivalent; integracja z
  istniejącym Pythonem (HARE) byłaby trudniejsza.
- **Node.js / TypeScript** — odrzucone: mniej dojrzałe biblioteki USB/serial
  na Linux.
- **Python 3.11** — odrzucone: 3.12 ma lepszą wydajność i `Self`.

## Notes

- `pyproject.toml` definiuje opcjonalne grupy (`ssh`, `usb`, `esp32`,
  `rp2040`, `all`) — minimal install dla H0 to tylko `pydantic + pyyaml +
  jsonschema + typer + rich + python-json-logger`.
- HIVE-IO firmware jest w C/C++ (osobne ADR i osobne repo).
