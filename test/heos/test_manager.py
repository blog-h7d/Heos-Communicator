import asyncio

import pytest

from heos.manager import HeosDeviceManager, HeosDevice, HeosEventCallback

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
    await asyncio.sleep(10)
    assert device.number_of_pings == 1
    await asyncio.sleep(52)
    assert device.number_of_pings == 2
    await device.stop_watcher()


@pytest.mark.device_needed
@pytest.mark.asyncio
async def test_scan_devices():
    heos_manager = HeosDeviceManager()
    await heos_manager.initialize(["192.168.178.20", ])
    assert heos_manager._all_devices


class A:

    @staticmethod
    @HeosEventCallback('test_event_2711')
    async def test():
        pass

    @staticmethod
    async def test2():
        pass

    @HeosEventCallback('test3_update', ['a', 'b'])
    async def test3(self):
        pass


def test_get_heos_decorators():
    data = HeosDeviceManager.get_heos_decorators(A)
    print(data)
    assert "test" in data
    assert data["test"][0]["name"] == "HeosEventCallback"
    assert data["test"][0]["event"] == "test_event_2711"
    assert "test2" not in data
    assert "test3" in data
    assert data["test3"][0]["name"] == "HeosEventCallback"
    assert data["test3"][0]["event"] == "test3_update"
    assert "a" in data["test3"][0]["params"]
    assert "b" in data["test3"][0]["params"]


def test_get_heos_decorators2():
    data = HeosDeviceManager.get_heos_decorators()
    print(data)
