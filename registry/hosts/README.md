# Hosts Registry

Katalog `registry/hosts/` zawiera manifesty hostów Linux (NUC, Jetson,
Raspberry Pi itp.) dostępnych przez SSH.

H0 przykład: `nuc-imp2-ros2-01.yaml`.

## Fingerprint klucza SSH (H4)

W H4 każdy host ma `identity.ssh.host_key_fingerprint` ustawiony na
`SHA256:...`. Pierwsze połączenie z nieznanym hostem → DEVICE_UNKNOWN +
wymaga jawnej akceptacji operatora.

H0 zezwala na `host_key_fingerprint: null` dla dev/test, ale
produkcyjne hosty MUSZĄ mieć ustawiony fingerprint.
