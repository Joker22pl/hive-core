# Threat Model — HIVE

> **Zakres:** HIVE Core + HIVE-IO + integracja z HARE.
> **Źródło prawdy:** [`vision.md`](vision.md), [`safety-model.md`](safety-model.md).

## 1. Co chronimy

| Zasób | Opis |
|-------|------|
| Urządzenia pod testami | ESP32, RP2040, hosty Linux — fizyczny hardware |
| Dane użytkownika | Manifesty, artefakty, evidence bundles, logi |
| Integralność firmware | Tylko `known-good` artefakty idą na docelowe urządzenie |
| Operator | Fizyczne bezpieczeństwo operatora i otoczenia |
| Środowisko sieciowe | hosty SSH, NUC, Jetson |

## 2. Kto jest przeciwnikiem

H0 identyfikuje następujących przeciwników (w kolejności prawdopodobieństwa):

| Przeciwnik | Motywacja | Zdolności |
|------------|-----------|-----------|
| **A1. Błąd HARE** (inżynier AI z błędem) | Nieumyślne podanie złego urządzenia / artefaktu | Wysokie (HARE ma dużo swobody) |
| **A2. Błąd operatora** | Podłączenie złego urządzenia, literówka w ID | Średnie |
| **A3. Błąd sieci** | Utrata SSH / USB / WiFi | Wysokie (środowisko domowe) |
| **A4. Wadliwy hardware** | Kabel bez danych, martwy MCU, zła masa | Średnie |
| **A5. Atakujący z sieci lokalnej** | MITM, wstrzyknięcie komend | Niskie (sieć domowa) |
| **A6. Atakujący fizyczny** | Fizyczny dostęp do HIVE-IO | Niskie (fizyczna kontrola) |

H0 nie uwzględnia: A7 (zaawansowany persistent threat, APT) ani A8 (atak
na łańcuch dostaw hardware). To są poza zakresem projektu hobbystycznego.

## 3. Drzewa ataku (uproszczone STRIDE-per-element)

### 3.1 Flash złego artefaktu na złe urządzenie

```
Główny scenariusz:
  HARE → HIVE Core → esptool → ESP32 (motor controller)
  → ESP32 dostaje firmware z innego projektu / test target

  Wektory:
  - HARE podaje zły artifact_id            (A1)
  - Manifest urządzenia ma zły VID/PID     (A2, A5)
  - Rejestr urządzeń nie jest aktualny     (A2)
  - Multiple device match → AMBIGUOUS       (A2)

  Mitygacja:
  - Identyfikacja wyłącznie MATCH_CONFIRMED (L1)
  - Lock per device (L2)
  - Pre-flight check w manifeście
  - Recovery strategy z rollback do known-good

  Ryzyko rezydualne: NISKIE (wymaga 3 niezależnych błędów)
```

### 3.2 Utrata kontroli nad silnikami podczas flash

```
Główny scenariusz:
  flash trwa → WiFi/USB padło → MCU zostaje w stanie "bootloader"
  → operator traci kontrolę nad robotem

  Wektory:
  - Utrata SSH/USB mid-flash                  (A3)
  - MCU restartuje się do trybu app w trakcie   (A4)

  Mitygacja:
  - MOTOR_ENABLE=OFF przed flash (L3)
  - HIVE-IO utrzymuje safe_state przy utracie heartbeat
  - Procedura recovery (bootloader reflash) jest idempotentna
  - Bezpieczny restart do IDLE (robotics-safety-review, punkt 13)

  Ryzyko rezydualne: NISKIE (L3 + L4 mają niezależne warstwy)
```

### 3.3 MITM na SSH do hosta Linux

```
Główny scenariusz:
  HIVE Core → SSH do NUC → NUC wykonuje komendy z recovery
  → atakujący w sieci lokalnej podszywa się pod NUC

  Wektory:
  - Brak weryfikacji fingerprintu hosta        (A5)
  - Atakujący kontroluje DNS / ARP            (A5)

  Mitygacja:
  - Manifest hosta zawiera ssh.host_key_fingerprint
  - HIVE odrzuca połączenie jeśli fingerprint != manifest
  - Pierwsze połączenie z nieznanym hostem → DEVICE_UNKNOWN

  Ryzyko rezydualne: NISKIE
```

### 3.4 Błędna decyzja recovery (recovery loops)

```
Główny scenariusz:
  Flash fails → recovery runs → flash again → fails → recovery again...
  → hardware uszkodzony, HIVE próbuje bez końca

  Wektory:
  - Brak limitu prób                          (A1, A2)
  - Brak eskalacji                             (A1)

  Mitygacja:
  - max_attempts per recovery                 (H0: model)
  - escalate_to_human_after                   (H0: model)
  - Recovery nie woła recovery                (L4)

  Ryzyko rezydualne: NISKIE
```

### 3.5 Wyciek sekretów (SSH keys, host fingerprints)

```
Główny scenariusz:
  Manifest hosta w git zawiera klucz SSH      (A2, A5)

  Wektory:
  - Literal SSH key w YAML                     (A2)
  - Token w pre-commit                         (A5)

  Mitygacja:
  - Manifest używa credential_reference, nie klucza
  - gitleaks w pre-commit (konwencja WORKFLOW.md)
  - Wzorz `.env` w .gitignore

  Ryzyko rezydualne: NISKIE (przy działającym gitleaks)
```

### 3.6 Nieautoryzowany dostęp do HIVE-IO

```
Główny scenariusz:
  Fizyczny atakujący wpina swoje USB w HIVE-IO
  → kontroluje silniki / RESET / BOOT

  Wektory:
  - Brak autoryzacji na USB CDC               (A6)
  - Brak hasła na fizycznym dostępie           (A6)

  Mitygacja:
  - HIVE-IO jest w obudowie, dostęp ograniczony fizycznie
  - W przyszłości: HMAC autoryzacja (H5+)
  - HIVE-IO nie przyjmuje komend bez ack heartbeat (H2+)

  Ryzyko rezydualne: ŚREDNIE (fizyczny dostęp = duża siła)
```

## 4. Mitigacje horyzontalne

Niezależnie od scenariusza:

- **Audit:** każda operacja sprzętowa → evidence bundle z hashem.
- **Fail-safe defaults:** HIVE-IO startuje w `safe_state`; recovery wraca
  do `known-good`; lock z TTL zapobiega zombie operacjom.
- **Defense in depth:** 4 warstwy bezpieczeństwa (identyfikacja, lock,
  safe state, E-stop) — awaria jednej nie powoduje awarii pozostałych.
- **Principle of least privilege:** HARE nie ma bezpośredniego dostępu do
  hardware — tylko do wysokopoziomowego API.
- **Eskalacja:** recovery ma warunek eskalacji do człowieka.

## 5. Założenia i ograniczenia

H0 zakłada:

- sieć domowa (nie korporacyjna), atakujący nie ma fizycznego dostępu,
- operator jest jedynym użytkownikiem (brak multi-tenant),
- HARE nie jest celem ataku (jest zaufanym agentem właściciela),
- sprzęt jest kontrolowany przez Jokera (brak łańcucha dostaw).

Poza zakresem H0:

- kryptograficzne podpisy artefaktów (H3+),
- HMAC autoryzacja HIVE-IO (H5+),
- szyfrowanie evidence bundles at-rest (H3+),
- hardening SSH bastion (poza projektem),
- pełny formalny threat model (NIST/STRIDE) — roboczy STRIDE powyżej jest
  wystarczający dla projektu hobbystycznego.

## 6. Out-of-scope H0

- Redukcja ryzyka przez hardware (np. watchdogs na wszystkich kanałach
  zasilania — H2+).
- Formal certification (np. ISO 13849) — projekt hobbystyczny.
- Penetration testing (H5+).

H0 dostarcza **przeglądową klasyfikację zagrożeń** i **mapowanie mitigacji**.
Pełny formalny threat model (STRIDE/PASTA) jest planowany na H5+.
