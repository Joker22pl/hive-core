# Roadmap — HIVE

> **Status:** H0 w toku. Roadmap jest **planowana**, nie obiecywana.

## H0 — Fundament ✅ w toku

- [x] Repozytoria `hive-core` + `hive-io`
- [x] README + LICENSE + .gitignore + .editorconfig + .pre-commit-config
- [x] Schematy JSON: device, artifact, verification-profile, evidence-bundle
- [x] Manifesty przykładowe w `registry/`
- [x] Modele Pydantic dla urządzeń, artefaktów, locków, profilów, evidence
- [x] Specyfikacja protokołu HIVE Core ↔ HIVE-IO
- [x] Threat model (roboczy STRIDE)
- [x] Model bezpieczeństwa (4 warstwy)
- [x] Model recovery
- [x] Model artefaktów
- [x] Model identyfikacji urządzeń
- [x] Szkielety modułów (`src/hive/`)
- [x] Szkielety CLI (`hive system/device/io/lock/artifact/flash/verify/recover/evidence`)
- [x] Testy walidacji schematów + smoke testy modeli
- [x] ADR (6 sztuk)
- [x] Raport końcowy `HIVE-H0-EVIDENCE-REPORT.md`

**NIE w H0 (świadomie):** real I/O (USB/serial/SSH), SQLite, REST API, real flashing,
real HIVE-IO firmware.

## H1 — Device Discovery

- Real USB discovery (`pyudev`) z cache i subskrypcją zdarzeń
- Serial discovery (`pyserial`) — wykrywanie portów, stabilnych ścieżek
- Udev rule installer (tworzenie `stable_path` aliasów)
- Rejestr urządzeń jako SQLite DB z migracjami (alembic)
- SSH discovery (skan LAN, fingerprint collection)
- CLI: `hive device scan`, `hive device list`, `hive device inspect`, `hive device register`
- In-memory + JSON lock store → SQLite lock store
- Lock sweeper (porzucone locki)
- Pierwsze uruchomienie z rzeczywistym sprzętem na stole

**Kryterium akceptacji:** `hive device scan` zwraca listę urządzeń z
`IdentificationStatus`; `hive device register` zapisuje nowy manifest do SQLite;
`hive lock list` pokazuje aktywne locki.

## H2 — HIVE-IO Firmware + Protocol Client

- Firmware HIVE-IO (RPi Pico, C/C++, Pico SDK, USB CDC, JSON Lines)
- Maszyna stanów w firmware (BOOT → IDLE → ACTIVE → FAULT → SAFE)
- Hardware watchdog + heartbeat monitoring
- E-stop handling z fizycznym debounce
- Klient HIVE Core (`hive.io_controller.client.HiveIOClient`) z timeoutami
  i retry
- Mock HIVE-IO (do testów integracyjnych bez fizycznego sprzętu)
- Schemat blokowy + finalny BOM (po prototypie modułowym)
- Pierwszy prototyp modułowy HIVE-IO (Pico + load switch + optoizolacja)

**Kryterium akceptacji:** HIVE-IO raportuje `get_status` przez USB CDC;
mock przechodzi testy integracyjne; firmware weryfikowalny na stole.

## H3 — Flashing + Artifact Registry + Rollback

- ESP32 adapter (esptool): enter_bootloader, flash, reset
- RP2040 adapter (picotool + UF2): BOOTSEL, copy, reset
- Artifact builder (idf.py, picotool build) + SHA-256 + manifest
- Artifact registry (SQLite, statuses: built → tested → verified → known-good)
- Recovery executor (real execution strategii z recovery-model.md)
- Evidence bundle generator (pełny, z logami)
- CLI: `hive artifact build`, `hive artifact list`, `hive artifact inspect`,
  `hive artifact mark-known-good`, `hive flash`, `hive verify`, `hive recover`,
  `hive evidence show`
- Pierwszy end-to-end: ESP32 build → flash → verify → evidence

**Kryterium akceptacji:** pełny cykl flash-and-verify na prawdziwym ESP32
z działającym HIVE-IO; rollback do known-good działa; evidence bundle
kompletny.

## H4 — Linux + ROS 2 przez SSH

- SSH adapter (paramiko): exec, copy, service restart
- Host registry (NUC, Jetson, RPi)
- Linux verification profiles (`linux-ssh-health`, `ros2-basic-health`)
- ROS 2 Jazzy health check (nodes/topics/services, `ROS_DOMAIN_ID`)
- Deploy pipeline (artefakt → host → service)
- CLI: `hive deploy`, `hive ssh-exec` (tylko kontrolowane komendy)

**Kryterium akceptacji:** deploy ROS 2 workspace na NUC przez SSH; verify
profile `ros2-basic-health` przechodzi na działającym systemie.

## H5 — HARE Integration

- FastAPI serwer dla HIVE (zgodnie z kontraktem API)
- HMAC autoryzacja HIVE-IO (planned w H2+, finalized w H5)
- HARE client lib (`hare.hive_client.HiveClient`)
- Misje HARE mapowane na profile weryfikacyjne HIVE
- Closed-loop improvement: HARE czyta evidence bundles i aktualizuje
  swoje decyzje
- Multi-controller HIVE-IO

**Kryterium akceptacji:** HARE wykonuje misję `build+flash+verify` na
prawdziwym urządzeniu autonomicznie, z pełnym evidence trailem.

## H6 — Hardware-in-the-Loop

- Sterowniki silników (DRV8835, BTS7960, ODrive) — adaptery HIVE
- Enkodery, czujniki prądu, IMU
- Testy HIL: profile `hil-motor-basic`, `hil-encoder-calibration`
- Integracja z `robotics-bringup` skill (gaja-robotics)

**Kryterium akceptacji:** profile HIL wykonywane automatycznie z pełnym
bezpieczeństwem (MOTOR_ENABLE, E-stop, watchdog zgodnie z
[`robotics-safety-review`](../..)).

## H7 — Distributed HIVE

- Zdalne gatewaye (np. Raspberry Pi 1 jako HIVE Gateway udostępniający
  UART/USB/programatory przez sieć)
- Klient HIVE Gateway (TCP/UDP wrapper na ten sam protokół)
- Multi-host orchestration (jeden HIVE Core, wiele bramek)
- Audit replication

**Kryterium akceptacji:** HIVE Gateway forwarduje USB CDC z HIVE-IO
przez sieć; flash przez gateway ma te same gwarancje co flash lokalny.

---

## Notatki

- Roadmap jest **iteracyjny**. Etapy mogą być łączone lub dzielone.
- Priorytet: H1 → H2 → H3 muszą być sekwencyjne (każdy buduje na poprzednim).
- H4 i H5+ mogą iść równolegle z testami H1–H3 na stole.
- H6 jest zależny od fizycznego sprzętu robotów (IMP2, ARP-AGRI).
- H7 jest daleką przyszłością; zależy od sieci LAN i fizycznego dostępu do
  wielu lokalizacji.
