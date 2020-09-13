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
@pytest.mark.parametrize("play_state", ["play", "pause", "stop"])
async def test_set_play_state(monkeypatch, heos_device, play_state: str):
    has_run = False
    heos_device.play_state = ''

    async def mock_telnet(ip, command):
        nonlocal play_state
        assert command == b'heos://player/set_play_state?pid=1234&state=' + play_state.encode()

        nonlocal has_run
        has_run = True

        return {
            "heos": {
                "command": "player/set_play_state",
                "result": "success",
                "message": "pid=1234&state=" + play_state
            }
        }

    monkeypatch.setattr(HeosDeviceManager, "send_telnet_message", mock_telnet)

    assert await heos_device.set_play_state(play_state)
    assert has_run
    assert heos_device.play_state == play_state


@pytest.mark.asyncio
async def test_set_play_state_invalid(monkeypatch, heos_device):
    assert not await heos_device.set_play_state('playing')
    assert not await heos_device.set_play_state('')


@pytest.mark.asyncio
async def test_set_volume(monkeypatch, heos_device):
    has_run = False
    heos_device.volume = 0

    async def mock_telnet(ip, command):
        assert command == b'heos://player/set_volume?pid=1234&level=78'
        nonlocal has_run
        has_run = True
        return {
            "heos": {
                "command": "player/set_volume",
                "result": "success",
                "message": "pid=1234&level=78"
            }
        }

    monkeypatch.setattr(HeosDeviceManager, "send_telnet_message", mock_telnet)

    assert await heos_device.set_volume(78)
    assert has_run
    assert heos_device.volume == 78


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
