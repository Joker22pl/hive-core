# PROMPT DLA GAIA-ROBOTIC — UTWORZENIE PROJEKTU HIVE

Tworzymy nowy projekt robotyczno-infrastrukturalny o nazwie:

# HIVE — Hermes Integration & Verification Environment

HIVE ma być kontrolowanym środowiskiem integracji, programowania, flashowania, testowania, diagnostyki i odzyskiwania urządzeń wykorzystywanych w projektach robotycznych.

Projekt ma współpracować z agentem HARE, ale ma pozostać od niego niezależny.

## 1. Rola HIVE w ekosystemie

Przyjmij następujący podział odpowiedzialności:

* **Gaia-Robotic** — architekt techniczny i opiekun projektów robotycznych.
* **HARE** — warstwa wykonawcza realizująca zadania inżynierskie: programowanie, budowanie, flashowanie, wdrażanie, testowanie i poprawianie kodu.
* **HIVE** — bezpieczne środowisko sprzętowo-programowe udostępniające urządzenia, stanowiska testowe, procedury flashowania, testy, recovery i dowody wykonania.
* **HEOS** — zasady organizacji wiedzy, artefaktów, lifecycle i governance.

Podstawowa zasada:

> HARE decyduje, jak wykonać pracę inżynierską, ale wszystkie operacje na sprzęcie wykonuje przez kontrolowane API HIVE.

HARE nie powinien bezpośrednio wykonywać niekontrolowanych poleceń na losowo wykrytych portach USB, GPIO, przekaźnikach ani urządzeniach.

---

# 2. Cel projektu

HIVE ma umożliwić bezpieczny, audytowalny i możliwie autonomiczny cykl:

```text
wykrycie urządzenia
→ jednoznaczna identyfikacja
→ rezerwacja zasobu
→ przygotowanie bezpiecznego stanu
→ budowa artefaktu
→ flashowanie lub wdrożenie
→ uruchomienie
→ test
→ zebranie wyników
→ diagnoza
→ poprawka
→ ponowny test
→ zatwierdzenie lub rollback
```

HIVE musi odpowiadać na pytania:

1. Jakie urządzenie zostało podłączone?
2. Do którego projektu i roli jest przypisane?
3. Jakie operacje są na nim dozwolone?
4. Jaki firmware lub software powinien być uruchomiony?
5. Jak sprawdzić poprawność wdrożenia?
6. Jak wrócić do znanego działającego stanu?
7. Jakie dowody potwierdzają wykonanie operacji?

Najważniejsza zasada bezpieczeństwa:

> Brak jednoznacznej identyfikacji urządzenia oznacza bezwzględny zakaz flashowania.

---

# 3. Docelowa architektura

## 3.1 HIVE Core

HIVE Core ma działać na głównym serwerze `gajaserv`, czyli Intel NUC z Ubuntu Server 24.04.

HIVE Core odpowiada za:

* rejestr urządzeń,
* wykrywanie USB i portów szeregowych,
* zarządzanie połączeniami SSH,
* budowanie firmware,
* rejestr artefaktów,
* flashowanie,
* testy,
* blokowanie urządzeń,
* recovery i rollback,
* zbieranie logów,
* generowanie evidence bundles,
* bazę stanu operacyjnego,
* CLI,
* przyszłe REST API dla HARE i HDS.

Nie używaj Raspberry Pi 1 jako głównego komputera HIVE.

Raspberry Pi 1 może zostać później wykorzystane jako opcjonalny zdalny HIVE Gateway udostępniający UART, USB lub programatory przez sieć. Nie należy uwzględniać go w MVP poza opisaniem przyszłej możliwości.

## 3.2 HIVE-IO

Osobne Raspberry Pi Pico ma zostać wykorzystane jako sprzętowy kontroler stanowiska testowego o nazwie:

```text
HIVE-IO
```

HIVE-IO będzie połączone z HIVE Core przez USB CDC.

HIVE-IO ma odpowiadać za:

* sterowanie kanałami zasilania,
* sterowanie liniami RESET,
* sterowanie liniami BOOT,
* sprzętowy sygnał `MOTOR_ENABLE`,
* odczyt fizycznego E-stopu,
* watchdog,
* heartbeat,
* wymuszanie bezpiecznego stanu,
* raportowanie rzeczywistych stanów wyjść i wejść.

HIVE-IO nie może być jednocześnie urządzeniem testowym.

Docelowy układ:

```text
Raspberry Pi Pico A → stały kontroler HIVE-IO
Raspberry Pi Pico B → urządzenie rozwojowe i testowe
```

---

# 4. Zakres urządzeń MVP

Pierwsza wersja HIVE musi obsługiwać trzy klasy urządzeń.

## 4.1 ESP32-S3 Pico

Zakres:

* wykrywanie USB,
* identyfikacja układu,
* VID/PID,
* numer seryjny, jeżeli jest dostępny,
* stabilny alias urządzenia,
* wejście w bootloader,
* reset,
* flashowanie,
* monitor UART,
* test sygnatury startowej,
* test komunikacji,
* test micro-ROS,
* obsługa known-good firmware,
* rollback,
* evidence bundle.

## 4.2 Raspberry Pi Pico / RP2040

Zakres:

* identyfikacja urządzenia,
* wykrywanie trybu normalnego i BOOTSEL,
* flashowanie UF2,
* obsługa `picotool`, jeśli będzie użyteczne,
* reset,
* monitor USB lub UART,
* odczyt wersji firmware,
* test komunikacji,
* rollback lub ponowne wgranie known-good firmware.

## 4.3 Linux i ROS 2 przez SSH

Zakres:

* hosty Ubuntu,
* NUC,
* Jetson,
* Raspberry Pi,
* urządzenia ROS 2,
* połączenie przez SSH,
* kontrola fingerprintu klucza hosta,
* identyfikacja hosta,
* wykonywanie kontrolowanych poleceń,
* przesyłanie artefaktów,
* obsługa systemd,
* uruchamianie i restartowanie usług,
* zbieranie logów,
* sprawdzanie ROS 2 Jazzy,
* sprawdzanie nodów, topiców, services i actions,
* sprawdzanie `ROS_DOMAIN_ID`,
* podstawowy ROS 2 health check.

---

# 5. Repozytoria

Utwórz dwa osobne repozytoria:

```text
hive-core
hive-io
```

## 5.1 Repozytorium `hive-core`

Zawartość początkowa:

```text
hive-core/
├── README.md
├── LICENSE
├── .gitignore
├── pyproject.toml
├── docs/
│   ├── architecture.md
│   ├── safety-model.md
│   ├── device-identity.md
│   ├── artifact-lifecycle.md
│   ├── verification-model.md
│   ├── recovery-model.md
│   ├── threat-model.md
│   └── roadmap.md
├── schemas/
│   ├── device.schema.json
│   ├── artifact.schema.json
│   ├── verification-profile.schema.json
│   └── evidence-bundle.schema.json
├── registry/
│   ├── devices/
│   ├── boards/
│   ├── hosts/
│   └── programmers/
├── src/hive/
│   ├── cli/
│   ├── discovery/
│   ├── registry/
│   ├── artifacts/
│   ├── adapters/
│   │   ├── usb/
│   │   ├── serial/
│   │   ├── esp32/
│   │   ├── rp2040/
│   │   └── ssh/
│   ├── verification/
│   ├── locking/
│   ├── recovery/
│   ├── evidence/
│   ├── database/
│   └── io_controller/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── examples/
```

## 5.2 Repozytorium `hive-io`

Zawartość początkowa:

```text
hive-io/
├── README.md
├── LICENSE
├── .gitignore
├── CMakeLists.txt
├── docs/
│   ├── hardware-architecture.md
│   ├── pinout.md
│   ├── protocol.md
│   ├── safety-states.md
│   ├── watchdog.md
│   └── wiring-guide.md
├── firmware/
│   ├── src/
│   ├── include/
│   └── tests/
├── hardware/
│   ├── block-diagram.md
│   ├── bom.md
│   └── schematics/
├── tools/
└── examples/
```

Repozytoria mają zostać dodane do centralnego repozytorium `gaja-projekty`.

Zastosuj obowiązujące konwencje:

* konto GitHub: `Joker22pl`,
* README opisujące cel, status, architekturę, stack i sposób uruchomienia,
* `.gitignore`,
* licencja MIT jako domyślna,
* wpis w hubie `gaja-projekty`,
* commity po angielsku,
* format commitów:

```text
[tag] description
```

Dozwolone podstawowe tagi:

```text
[init]
[add]
[fix]
[doc]
[refactor]
[test]
[security]
```

---

# 6. Technologie

## HIVE Core

Preferowany stack:

* Python 3.12,
* `pyudev`,
* `pyserial`,
* `paramiko` lub bezpieczny wrapper systemowego OpenSSH,
* `esptool`,
* `picotool`,
* `pytest`,
* YAML,
* JSON Schema,
* SQLite,
* Pydantic,
* Typer dla CLI,
* structured logging,
* SHA-256 dla artefaktów,
* Git jako źródło prawdy dla deklaratywnych manifestów.

REST API nie jest obowiązkowe w etapie H0. Architektura ma jednak umożliwiać jego późniejsze dodanie.

Nie wprowadzaj w MVP:

* Kubernetesa,
* rozbudowanego brokera wiadomości,
* mikroserwisów,
* chmury,
* skomplikowanego frontendu,
* zależności, które nie mają bezpośredniej wartości dla MVP.

Preferuj prosty lokalny system modułowy działający na `gajaserv`.

## HIVE-IO

Preferowany stack:

* C lub C++,
* Raspberry Pi Pico SDK,
* USB CDC,
* JSON Lines jako protokół MVP,
* sprzętowy watchdog,
* jawna maszyna stanów,
* testowalne moduły logiki.

Nie używaj MicroPythona w wersji docelowej HIVE-IO.

MicroPython można wykorzystać jedynie do krótkiego eksperymentu, jeżeli będzie to dobrze uzasadnione.

---

# 7. Model urządzenia

Każde urządzenie musi mieć trwały manifest.

Przykład:

```yaml
device_id: esp32s3-imp2-motor-01
display_name: IMP2 motor controller
type: microcontroller
board: esp32-s3-pico
project: IMP2
role: motor-controller

identity:
  usb_vid: "303A"
  usb_pid: "1001"
  serial_number: null
  stable_path: /dev/hive/imp2-motor-controller

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
  known_good_artifact: null

safety:
  motor_power_required: false
  motor_enable_must_be_off_during_flash: true
  automatic_power_cycle_allowed: true
  automatic_flash_allowed: true

recovery:
  strategy: esp32-bootloader-reflash
```

Nie wolno opierać identyfikacji wyłącznie na:

```text
/dev/ttyUSB0
/dev/ttyACM0
adresie IP
nazwie hosta
```

Identyfikacja powinna wykorzystywać kombinację dostępnych cech oraz rejestr urządzeń.

---

# 8. Stany identyfikacji

Zdefiniuj między innymi następujące statusy:

```text
MATCH_CONFIRMED
MATCH_AMBIGUOUS
DEVICE_UNKNOWN
DEVICE_OFFLINE
DEVICE_BUSY
PROJECT_MISMATCH
ROLE_MISMATCH
FIRMWARE_INCOMPATIBLE
RECOVERY_REQUIRED
SAFETY_INTERLOCK_OPEN
ESTOP_ACTIVE
```

Tylko stan:

```text
MATCH_CONFIRMED
```

może pozwolić na autonomiczne flashowanie.

---

# 9. Rejestr artefaktów

Każdy zbudowany firmware lub pakiet wdrożeniowy musi posiadać manifest zawierający:

* unikalny identyfikator,
* nazwę projektu,
* target sprzętowy,
* commit Git,
* dirty state repozytorium,
* hash SHA-256,
* datę budowy,
* wersję toolchainu,
* profil kompilacji,
* wyniki testów,
* kompatybilne urządzenia,
* status artefaktu,
* informację, czy jest known-good,
* powiązany evidence bundle.

Proponowane statusy artefaktu:

```text
built
tested
verified
known-good
rejected
superseded
archived
```

Nie traktuj nazwy pliku jako wystarczającego identyfikatora artefaktu.

---

# 10. Resource locking

HIVE musi uniemożliwiać jednoczesne używanie tego samego urządzenia przez kilka procesów lub agentów.

Każda operacja sprzętowa musi:

1. uzyskać blokadę urządzenia,
2. posiadać właściciela,
3. posiadać identyfikator sesji,
4. posiadać czas wygaśnięcia lease,
5. odnawiać lease podczas działania,
6. bezpiecznie zwolnić blokadę,
7. obsługiwać porzucone blokady.

Przykład:

```yaml
device_id: esp32s3-imp2-motor-01
owner: hare
session_id: hive-run-20260730-001
operation: firmware-verification
lease_expires_at: 2026-07-30T04:00:00+02:00
```

---

# 11. HIVE-IO — wymagania sprzętowe

Pierwsza wersja HIVE-IO powinna przewidywać:

* minimum 4 kanały sterowania zasilaniem,
* minimum 2 linie RESET,
* minimum 1 linię BOOT,
* osobny sygnał `MOTOR_ENABLE`,
* wejście E-stop,
* diodę statusową,
* watchdog,
* heartbeat,
* możliwość wymuszenia stanu bezpiecznego,
* odczyt rzeczywistych stanów kanałów.

Przykładowe kanały:

```text
POWER_ESP32_1
POWER_PICO_1
POWER_SENSOR_1
POWER_AUX_1
RESET_ESP32_1
BOOT_ESP32_1
RESET_PICO_1
MOTOR_ENABLE
ESTOP_SENSE
```

Raspberry Pi Pico nie może bezpośrednio zasilać urządzeń ani większych obciążeń.

GPIO ma sterować odpowiednio dobranymi:

* load switchami,
* tranzystorami MOSFET,
* przekaźnikami,
* wejściami enable,
* izolowanymi modułami sterującymi.

Przygotuj w dokumentacji:

* schemat blokowy,
* rekomendowaną topologię,
* wstępny BOM,
* podział na domenę logiki i napędów,
* wytyczne dla E-stopu,
* zasady wspólnej masy i izolacji,
* ograniczenia prądowe,
* ostrzeżenia dotyczące GPIO 3,3 V.

Nie projektuj jeszcze finalnej płytki PCB, chyba że wynika to bezpośrednio z analizy. Najpierw przygotuj bezpieczny prototyp modułowy.

---

# 12. Stan bezpieczny

HIVE-IO musi domyślnie uruchamiać się w stanie:

```text
MOTOR_ENABLE = OFF
motor power = OFF
autonomous motion = FORBIDDEN
BOOT signals = INACTIVE
RESET signals = RELEASED
```

Utrata komunikacji lub heartbeat musi powodować:

1. natychmiastowe wyłączenie `MOTOR_ENABLE`,
2. przejście do stanu bezpiecznego,
3. przerwanie aktywnego testu ruchu,
4. zgłoszenie zdarzenia `CONTROL_LINK_LOST`,
5. zachowanie zasilania logiki tylko wtedy, gdy jest to bezpieczne.

Stan E-stop musi mieć wyższy priorytet niż polecenia HIVE Core.

Polecenie programowe nie może obejść aktywnego E-stopu.

---

# 13. Protokół HIVE Core ↔ HIVE-IO

W MVP zastosuj:

```text
USB CDC + JSON Lines
```

Każde polecenie musi posiadać:

* `request_id`,
* nazwę komendy,
* parametry,
* odpowiedź,
* kod wyniku,
* obserwowany stan.

Przykład:

```json
{"request_id":"req-001","command":"power_set","channel":"esp32_1","state":true}
```

Odpowiedź:

```json
{"request_id":"req-001","result":"ok","channel":"esp32_1","observed_state":true}
```

Przewidź komendy:

```text
get_status
get_capabilities
heartbeat
safe_state
power_set
power_cycle
reset_pulse
boot_set
motor_enable_set
estop_status
firmware_version
```

Protokół ma być wersjonowany.

Zaprojektuj go tak, aby w przyszłości można było dodać:

* CRC,
* format binarny,
* uwierzytelnianie,
* kilka kontrolerów HIVE-IO,
* komunikację sieciową przez gateway.

---

# 14. Profile weryfikacyjne

Przygotuj model deklaratywnych profili testowych.

Minimalne profile:

```text
build-only
flash-and-boot
serial-smoke-test
esp32-basic-health
rp2040-basic-health
microros-connectivity
linux-ssh-health
ros2-basic-health
```

Przykład profilu:

```yaml
profile_id: esp32-basic-health
target_type: esp32-s3-pico

preconditions:
  - device_match_confirmed
  - motor_enable_off
  - artifact_compatible

steps:
  - enter_bootloader
  - flash_artifact
  - reset_device
  - wait_for_serial
  - assert_boot_signature
  - collect_serial_logs

success:
  all_steps_passed: true

failure:
  collect_evidence: true
  attempt_recovery: true
  rollback_to_known_good: false
```

Testy muszą zwracać ustrukturyzowane wyniki, a nie tylko log tekstowy.

Przykład:

```yaml
result: failed
failure_class: serial_boot_timeout
expected: boot_signature_within_10s
observed: no_serial_output
suggested_recovery:
  - power_cycle
  - enter_bootloader
  - reflash_known_good
```

---

# 15. Evidence bundle

Każda istotna operacja powinna generować evidence bundle.

Minimalna zawartość:

* identyfikator operacji,
* identyfikator urządzenia,
* manifest urządzenia,
* artefakt i jego hash,
* commit Git,
* informacje o środowisku,
* wersje narzędzi,
* komendy i parametry,
* log budowania,
* log flashowania,
* log urządzenia,
* wynik każdego testu,
* zdarzenia bezpieczeństwa,
* decyzje recovery,
* informacja o rollbacku,
* czas rozpoczęcia i zakończenia,
* finalny status.

Evidence bundle powinien być przechowywany w formacie możliwym do automatycznej analizy i ręcznego audytu.

---

# 16. Recovery i rollback

Zaprojektuj procedury recovery dla:

* ESP32-S3,
* Raspberry Pi Pico,
* hosta Linux dostępnego przez SSH,
* hosta Linux niedostępnego przez SSH,
* utraty portu szeregowego,
* zawieszenia urządzenia,
* nieudanego flashowania,
* niezgodnego firmware,
* utraty komunikacji z HIVE-IO.

Każde urządzenie powinno posiadać:

* procedurę resetu,
* procedurę power cycle,
* procedurę wejścia w bootloader,
* znany działający artefakt,
* warunki automatycznego rollbacku,
* limit prób recovery,
* warunek eskalacji do człowieka.

Recovery nie może wykonywać się w nieskończonej pętli.

---

# 17. CLI MVP

Zaprojektuj i przygotuj szkielet następujących komend:

```bash
hive system status

hive device scan
hive device list
hive device inspect <device-id>
hive device register <device-id>

hive artifact build
hive artifact list
hive artifact inspect <artifact-id>
hive artifact mark-known-good <artifact-id>

hive io status
hive io safe-state
hive io power <channel> on
hive io power <channel> off
hive io power-cycle <channel>
hive io reset <channel>

hive lock acquire <device-id>
hive lock release <device-id>
hive lock list

hive flash <device-id> --artifact <artifact-id>

hive verify run <device-id> --profile <profile-id>

hive recover <device-id>

hive evidence show <run-id>
hive evidence export <run-id>
```

Na etapie H0 komendy mogą być częściowo szkieletami, ale ich kontrakty, modele danych i przewidywane zachowanie mają być opisane.

---

# 18. Integracja z HARE

Nie implementuj pełnej integracji z HARE w pierwszym etapie.

Przygotuj jednak przyszły kontrakt wysokopoziomowego API:

```text
identify_device
reserve_device
release_device
build_artifact
flash_device
deploy_to_linux
run_verification
collect_evidence
recover_device
rollback_device
enter_safe_state
```

HARE nie powinien mieć bezpośredniego dostępu do:

* surowych GPIO,
* przekaźników,
* linii BOOT,
* linii RESET,
* zasilania napędów,
* przypadkowych portów `/dev/tty*`.

Wszystkie takie operacje mają przechodzić przez HIVE.

---

# 19. Zakres pierwszego etapu — H0

Zrealizuj teraz etap:

# H0 — Fundament projektu HIVE

Etap H0 ma obejmować:

1. analizę wymagań,
2. utworzenie dwóch repozytoriów,
3. dodanie ich do `gaja-projekty`,
4. dokumentację architektury,
5. model bezpieczeństwa,
6. threat model,
7. model urządzeń,
8. model artefaktów,
9. model profili weryfikacji,
10. model evidence bundles,
11. model resource locking,
12. model recovery,
13. projekt protokołu HIVE Core ↔ HIVE-IO,
14. schemat blokowy HIVE-IO,
15. wstępny BOM stanowiska,
16. szkielety kodu obu repozytoriów,
17. podstawowe testy modeli danych,
18. szkielety CLI,
19. plan etapów H1–H5,
20. raport końcowy z dowodami wykonania.

Nie wykonuj jeszcze rzeczywistego sterowania silnikami.

Nie uruchamiaj napięcia napędów.

Nie zakładaj, że konkretne urządzenie zostało poprawnie zidentyfikowane bez potwierdzenia manifestu.

---

# 20. Roadmapa

Przygotuj roadmapę:

## H0 — Fundament

Architektura, modele danych, bezpieczeństwo, repozytoria i szkielety.

## H1 — Device Discovery

USB, serial, udev, rejestr urządzeń, SSH discovery i stabilna identyfikacja.

## H2 — HIVE-IO

Firmware Pico, protokół, heartbeat, watchdog, zasilanie, reset, boot i E-stop.

## H3 — Flashing and Artifact Registry

ESP32-S3, RP2040, artefakty, known-good, rollback i evidence bundles.

## H4 — Linux and ROS 2

SSH, systemd, deployment, logi i testy ROS 2 Jazzy.

## H5 — HARE Integration

Bezpieczne API i closed-loop improvement.

## H6 — Hardware-in-the-Loop

Sterowniki silników, enkodery, czujniki, pomiary i testy całych podsystemów.

## H7 — Distributed HIVE

Zdalne gatewaye, w tym potencjalne wykorzystanie Raspberry Pi 1.

---

# 21. Kryteria akceptacji H0

Etap H0 można uznać za zakończony tylko wtedy, gdy:

* istnieją oba repozytoria,
* oba repozytoria mają poprawne README,
* projekty znajdują się w hubie `gaja-projekty`,
* architektura jest opisana,
* granice odpowiedzialności HARE i HIVE są jednoznaczne,
* istnieją schematy JSON dla głównych manifestów,
* schematy posiadają testy walidacji,
* istnieje model resource locking,
* istnieje model recovery,
* istnieje specyfikacja protokołu HIVE-IO,
* istnieje specyfikacja stanu bezpiecznego,
* istnieje threat model,
* istnieje wstępny BOM stanowiska,
* istnieje szkielet CLI,
* istnieje roadmapa H1–H7,
* wszystkie testy automatyczne przechodzą,
* repozytoria nie zawierają sekretów,
* dokumentacja jest spójna,
* został wygenerowany raport końcowy.

---

# 22. Zasady realizacji

Pracuj autonomicznie w zakresie:

* analizy,
* architektury,
* tworzenia repozytoriów,
* tworzenia dokumentacji,
* tworzenia schematów danych,
* tworzenia kodu,
* testów,
* commitów,
* aktualizacji hubu projektów.

Nie omijaj zasad bezpieczeństwa dla przyspieszenia prac.

Nie wprowadzaj nadmiernie skomplikowanej infrastruktury.

Preferuj rozwiązania:

* lokalne,
* proste,
* testowalne,
* audytowalne,
* możliwe do rozwijania,
* niezależne od chmury,
* odporne na błędną identyfikację urządzenia.

W przypadku decyzji architektonicznych:

1. opisz problem,
2. przedstaw rozważane opcje,
3. wybierz rozwiązanie,
4. zapisz uzasadnienie w ADR.

Wprowadź katalog:

```text
docs/adr/
```

i zapisuj istotne decyzje jako Architecture Decision Records.

---

# 23. Raport końcowy

Po wykonaniu etapu H0 przygotuj raport:

```text
HIVE-H0-EVIDENCE-REPORT.md
```

Raport musi zawierać:

1. streszczenie wykonanych prac,
2. listę utworzonych repozytoriów,
3. linki do repozytoriów,
4. aktualne commity,
5. strukturę katalogów,
6. opis architektury,
7. diagram przepływu HARE → HIVE → urządzenie,
8. model bezpieczeństwa,
9. model identyfikacji urządzeń,
10. model artefaktów,
11. model testów,
12. model recovery,
13. specyfikację HIVE-IO,
14. listę testów i ich wyniki,
15. wyniki walidacji schematów,
16. wykryte ryzyka,
17. otwarte decyzje,
18. ograniczenia aktualnej wersji,
19. propozycję zakresu H1,
20. konkretne dowody wykonania.

Dołącz:

* wyniki `git status`,
* wyniki testów,
* listę commitów,
* wersje użytych narzędzi,
* informacje o plikach utworzonych i zmodyfikowanych,
* potwierdzenie aktualizacji `gaja-projekty`.

Nie ograniczaj raportu do deklaracji. Każda ważna informacja powinna posiadać dowód możliwy do zweryfikowania.

jak skończysz poinformuj mnie i poczekaj na moja decyzje
