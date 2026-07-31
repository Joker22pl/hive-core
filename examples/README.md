# HIVE Core — examples

Runnable example scripts that exercise the public surface of HIVE Core
and double as living documentation.

All examples assume the working directory is the `hive-core/` project root.

## `manifest_validation.py`

Validate a single device manifest file against both the JSON Schema
(`schemas/device.schema.json`) and the Pydantic model
(`hive.common.models.device.DeviceManifest`).

```bash
python examples/manifest_validation.py registry/devices/esp32s3-imp2-motor-01.yaml
```

Exit code is 0 on success, 1 on validation failure, 2 on bad usage.

## `lock_service.py`

Demonstrates the lock service API end-to-end:

* in-memory store round-trip (acquire → renew → release),
* JSON-file store with disk persistence.

```bash
python examples/lock_service.py
```

## `mock_hive_io.py`

Demonstrates the mock HIVE-IO client and the test-hook surface:

* `MockHiveIOClient` for the wire-protocol surface,
* `get_test_hooks_for(client)` for the test-only ESTOP injection.

```bash
python examples/mock_hive_io.py
```

## `cli_round_trip.py`

End-to-end CLI round-trip using the JSON-file lock store. This is the
canonical "did it work" smoke test for H0.

```bash
python examples/cli_round_trip.py
```

See the script for the exact commands it runs.
