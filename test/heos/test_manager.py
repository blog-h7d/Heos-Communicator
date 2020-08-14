import asyncio

import pytest

from heos.manager import HeosDeviceManager, HeosDevice

heos_data = {
    "pid": "123",
    "name": "test",
    "model": "AVR1",
    "version": "1",
    "ip": "192.168.178.20",
    "network": "wifi",
    "serial": "ABC1",
}


@pytest.mark.asyncio
async def test_ping():
    device = HeosDevice(heos_data)
    assert device.number_of_pings == 0
    await device.start_watcher()
    await asyncio.sleep(3)
    assert device.number_of_pings == 2
    await device.stop_watcher()


@pytest.mark.device_needed
@pytest.mark.asyncio
async def test_scan_devices():
    heos_manager = HeosDeviceManager()
    await heos_manager.initialize(["192.168.178.20", ])
    assert heos_manager._all_devices
