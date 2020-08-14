import pytest

from heos.manager import HeosDeviceManager


@pytest.mark.device_needed
def test_scan_devices():
    heos_manager = HeosDeviceManager()
    heos_manager._scan_for_devices(["192.168.178.20", ])
    assert heos_manager._all_devices
