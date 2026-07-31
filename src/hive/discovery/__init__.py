"""Device discovery — USB / serial / SSH enumeration (H1).

Public surface:
    * DiscoveryService   — main entry point (USB + serial + SSH)
    * DiscoveredDevice   — device descriptor (USB / serial / SSH agnostic)
    * UsbAdapter         — wraps pyudev Context.enumerate()
    * SerialAdapter      — wraps pyserial.tools.list_ports
    * UdevRuleInstaller  — generates /etc/udev/rules.d/99-hive-*.rules
    * compute_fingerprint — SHA-256 fingerprint helper

H0 stub (raises NotImplementedInStageError) is kept as a fallback
when pyudev is not installed in the runtime. The CLI uses lazy
imports, so `hive --version` works without pyudev/pyserial installed.
"""

from __future__ import annotations

from hive.discovery.fingerprint import compute_fingerprint
from hive.discovery.models import DiscoveredDevice
from hive.discovery.serial import SerialAdapter
from hive.discovery.service import DiscoveryError, DiscoveryService
from hive.discovery.ssh import SshAdapter
from hive.discovery.udev import UdevError, UdevRule, UdevRuleInstaller
from hive.discovery.usb import Adapter, AdapterError, UsbAdapter

__all__ = [
    "Adapter",
    "AdapterError",
    "DiscoveredDevice",
    "DiscoveryError",
    "DiscoveryService",
    "SerialAdapter",
    "SshAdapter",
    "UdevError",
    "UdevRule",
    "UdevRuleInstaller",
    "UsbAdapter",
    "compute_fingerprint",
]