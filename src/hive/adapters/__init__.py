"""HIVE adapters — device-specific I/O.

H0: skeleton interfaces + NotImplementedInStageError on real I/O.
H1+: real implementations per adapter.
"""

from hive.adapters import esp32, rp2040, serial, ssh, usb
from hive.adapters.base import Adapter

__all__ = ["Adapter", "esp32", "rp2040", "serial", "ssh", "usb"]
