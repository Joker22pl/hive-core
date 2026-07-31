# Artifact Lifecycle

> **Źródło prawdy:** [`vision.md`](vision.md) sekcja 9 + schema
> [`../schemas/artifact.schema.json`](../schemas/artifact.schema.json).

## 1. Czym jest artefakt

**Artefakt** to wynik budowania firmware lub pakietu wdrożeniowego. Jest:

- **identyfikowalny** (UUID + SHA-256),
- **niezmienny** po zapisaniu (immutable content),
- **powiązany z manifestem** opisującym, jak powstał i dla kogo jest przeznaczony,
- **możliwy do śledzenia** przez Git commit + dirty state.

Nazwa pliku NIE jest wystarczającym identyfikatorem — stąd obowiązkowy
`artifact_id` (UUID v4) + `sha256` w manifeście.

## 2. Stany artefaktu

```text
built       # zbudowany, ale nie przeszedł jeszcze pełnej weryfikacji
tested      # przeszedł smoke test (np. boot signature)
verified    # przeszedł zadeklarowany profil weryfikacyjny
known-good  # wyznaczony jako fallback (zazwyczaj ostatni verified w danym oknie czasowym)
rejected    # test się nie powiódł i nie zostanie użyty
superseded  # zastąpiony przez nowszy verified artefakt dla tego samego targetu
archived    # wycofany z obiegu (np. po deprecation hardware)
```

Dozwolone przejścia:

```text
built    → tested → verified → known-good
                  ↘ rejected
verified → superseded → archived
known-good → superseded → archived  # gdy pojawia się nowy known-good
```

`known-good` jest **jedynym** stanem, z którego recovery może automatycznie
flashować (jeśli manifest urządzenia zezwala na `automatic_flash_allowed`).

## 3. Manifest artefaktu — minimalna zawartość

```yaml
artifact_id: a1b2c3d4-5678-90ab-cdef-1234567890ab
project: IMP2
target: esp32s3
target_board: esp32-s3-pico
target_role: motor-controller

git:
  repo: imp2-firmware
  commit_sha: "deadbeef1234567890abcdef1234567890abcdef"
  branch: main
  dirty: false                            # true jeśli working tree ma niezcommitowane zmiany

artifact:
  path: artifacts/imp2-motor-0.4.2.bin     # względna ścieżka w artifact store
  sha256: "f3e0d2c1..."                    # hash SHA-256 pliku
  size_bytes: 412344
  format: esp32-binary                     # esp32-binary | rp2040-uf2 | deb | tar.zst

build:
  toolchain_version: "esp-idf 5.2.1"
  build_profile: release
  build_host: gajaserv
  built_at: "2026-07-30T04:00:00+02:00"
  build_command: "idf.py build"
  build_duration_s: 47

compatible_devices:
  - esp32s3-imp2-motor-01
  - esp32s3-imp2-motor-02

tests:
  - profile_id: build-only
    result: passed
  - profile_id: flash-and-boot
    result: passed
  - profile_id: esp32-basic-health
    result: passed
    evidence_bundle_id: eb-2026-07-30-001

status: known-good                          # built | tested | verified | known-good | rejected | superseded | archived
superseded_by: null
evidence_bundle_id: eb-2026-07-30-001
```

Pełna walidacja przez `artifact.schema.json`.

## 4. Budowanie (H0: interfejs, H3: implementacja)

`hive.artifacts.builder.ArtifactBuilder` (interfejs w H0):

```python
from hive.artifacts.builder import ArtifactBuilder, BuildSpec

spec = BuildSpec(
    project="IMP2",
    target="esp32s3",
    source_repo="/home/gaja/imp2-firmware",
    commit_sha="deadbeef...",     # opcjonalnie; domyślnie HEAD
    build_profile="release",
    compatible_devices=["esp32s3-imp2-motor-01"],
)

builder = ArtifactBuilder(workdir="/home/gaja/.hive/work")
result = builder.build(spec)      # w H0 → NotImplementedError z komunikatem "H3"
```

W H3 builder uruchamia `idf.py build` (lub analogicznie dla RP2040 / Linux),
zbiera:

- plik wynikowy,
- logi budowania,
- wersje toolchainu,
- czas trwania,
- SHA-256 wyniku.

Po buildzie automatycznie wykonuje `build-only` profile (H3+).

## 5. Hash i integralność

Każdy artefakt ma `sha256` liczony **po zapisaniu** pliku wynikowego.
SHA-256 jest częścią `artifact_id` lookup: dwa artefakty o tej samej zawartości
mają ten sam hash, ale różne `artifact_id` (bo różne metadane).

W H0 liczymy hash na dowolnym pliku wskazanym w `ArtifactRef`:

```python
from hive.artifacts.hash import sha256_file
sha = sha256_file("/path/to/firmware.bin")
```

## 6. Magazyn artefaktów (H0: konwencja ścieżek)

```text
.hive/
├── artifacts/
│   └── <project>/
│       └── <artifact_id>/
│           ├── manifest.yaml
│           ├── firmware.bin          # lub .uf2 / .tar.zst / .deb
│           ├── build.log
│           └── verification/
│               ├── profile-build-only.log
│               └── profile-flash-and-boot.log
└── evidence/
    └── <bundle_id>/
        ├── bundle.yaml
        ├── device-manifest.yaml
        ├── artifact-manifest.yaml
        └── logs/
```

Ścieżki są konwencją — H0 waliduje je w testach, ale nie narzuca fizycznego
zapisu (to implementacja H3+).

## 7. Wersjonowanie i `known-good`

`known-good` jest **jedynym** stanem używanym przez recovery. Wyznaczanie
`known-good`:

- ręcznie: `hive artifact mark-known-good <artifact_id>`,
- automatycznie (opcjonalnie, H3+): po każdym `verified` w danym oknie czasowym
  bez `rejected`.

Nie ma globalnego "latest" — `known-good` jest jawnie wyznaczany. To zapobiega
sytuacji, w której ostatni build (który nie przeszedł jeszcze testu) zostaje
przypadkowo użyty jako fallback.

## 8. Superseded / archived

`superseded` pojawia się, gdy nowy `verified` artefakt dla tego samego targetu
zostaje wyznaczony jako `known-good`. Stary `known-good` automatycznie przechodzi
do `superseded`. To nie jest kasowanie — plik pozostaje, tylko zmienia się status.

`archived` jest stanem końcowym (ręczny). W H3+ będzie możliwe automatyczne
archiwizowanie po dłuższym czasie od `superseded`.

## 9. Bezpieczeństwo artefaktu

- Manifest artefaktu jest podpisywany kluczem build-host (H3+, opcjonalnie).
- SHA-256 jest **jedynym** sposobem porównywania zawartości.
- Artefakty z `dirty: true` w Git nie mogą zostać `known-good` (są tylko `tested`).
- Artefakty bez `evidence_bundle_id` nie mogą zostać `verified`.

## 10. Out-of-scope H0

- Real build execution (H3).
- Real artifact storage backend (H3+).
- Signing (H3+).
- Remote artifact server (H7).

H0 dostarcza **model danych + schema + interfejs budowniczego**. W H3 dochodzi
realne wykonanie.
