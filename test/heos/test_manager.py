import pytest

from heos.manager import HeosDevice, HeosDeviceManager, HeosEventCallback


@pytest.fixture
def heos_device():
    device = HeosDevice({
        'pid': '1234',
        'name': 'MockDevice',
        'model': 'mock',
        'version': '0.1',
        'ip': '127.0.0.1',
        'network': 'wlan',
        'serial': '1234567890',
    }, doUpdate=False)
    yield device


@pytest.mark.asyncio
async def test_ping(monkeypatch, heos_device):
    async def mock_telnet(ip, command):
        assert command == b'heos://system/heart_beat'
        return {
            "heos": {
                "command": "system/heart_beat ",
                "result": "success",
                "message": ""
            }
        }

    monkeypatch.setattr(HeosDeviceManager, "send_telnet_message", mock_telnet)

    assert await heos_device._ping()


@pytest.mark.asyncio
async def test_set_play_state(monkeypatch, heos_device):
    async def mock_telnet(ip, command):
        assert command == b'heos://player/set_play_state?pid=1234&state=play'
        return {
            "heos": {
                "command": "player/set_play_state",
                "result": "success",
                "message": "pid=1234&state=play"
            }
        }

    monkeypatch.setattr(HeosDeviceManager, "send_telnet_message", mock_telnet)

    assert await heos_device.set_play_state('play')


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
