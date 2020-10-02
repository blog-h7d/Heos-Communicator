import json

import pytest
import quart
import quart.flask_patch
import quart.testing

import controller
import heos.manager
from controller import app as app_for_testing, convert_to_dict


class DummyHeos(heos.manager.HeosDevice):
    def __init__(self):
        self.pid = "1234"
        self.name = "Dummy"
        self.model = "Dummy"
        self.version = "123"
        self.volume = 0

    async def set_play_state(self, play_state: str) -> bool:
        return True

    async def set_volume(self, volume: int):
        return True

    async def next_track(self):
        return True

    async def prev_track(self):
        return True


@pytest.fixture
async def client() -> quart.app.QuartClient:
    app_for_testing.config['TESTING'] = True
    yield app_for_testing.test_client()


@pytest.mark.asyncio
@pytest.mark.device_needed
@pytest.mark.timeout(20)
async def test_scan_for_devices():
    await controller.scan_for_devices(2)
    assert controller.found_heos_devices


@pytest.mark.asyncio
async def test_main_page_simple(client):
    response: quart.wrappers.Response

    response = await client.get('/')
    assert response.status_code == 200

    data = await response.get_data()
    assert data


@pytest.mark.asyncio
async def test_api_page_simple(client: quart.app.QuartClient):
    response: quart.wrappers.Response

    response = await client.get('/api/')
    assert response.status_code == 200

    data = await response.get_data()
    assert data
    json_data = json.loads(data)
    assert json_data
    assert 'network-devices' in json_data


@pytest.mark.asyncio
async def test_api_page_more(client: quart.app.QuartClient):
    if not controller.heos_manager:
        controller.heos_manager = heos.manager.HeosDeviceManager()

    controller.heos_manager._all_devices["1234"] = DummyHeos()

    response: quart.wrappers.Response
    response = await client.get('/api/')
    assert response.status_code == 200

    data = await response.get_data()
    assert data
    json_data = json.loads(data)
    assert json_data
    assert 'network-devices' in json_data
    assert 'heos-devices' in json_data
    assert len(json_data["heos-devices"]) > 0


@pytest.mark.asyncio
@pytest.mark.device_needed
async def test_devices_simple(client):
    response: quart.wrappers.Response

    response = await client.get('/devices/')
    assert response.status_code == 200

    raw_data = await response.get_data()
    data = json.loads(raw_data)

    assert data
    assert type(data) == list
    for device in data:
        assert 'name' in device
        assert 'host' in device
        assert 'port' in device


class ObjectDummy:
    param1 = "123"

    def __init__(self):
        self.p1 = "123"
        self._p2 = "abc"

    def dummy_func(self):
        pass


def test_convert_to_dict():
    obj = ObjectDummy()
    dic = convert_to_dict(obj)
    assert dic
    assert "param1" in dic
    assert dic["param1"] == "123"
    assert "dummy_func" not in dic

    assert "p1" in dic
    assert dic["p1"] == "123"
    assert "_p2" not in dic


@pytest.mark.asyncio
async def test_get_heos_devices(client):
    response: quart.wrappers.Response

    response = await client.get('/heos_devices/')
    assert response.status_code == 200

    raw_data = await response.get_data()
    data = json.loads(raw_data)

    assert type(data) == list


@pytest.mark.asyncio
async def test_get_heos_device_by_invalid_name(client):
    response: quart.wrappers.Response

    response = await client.get('/heos_device/test123/')
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_heos_device_by_name(client):
    response: quart.wrappers.Response

    if not controller.heos_manager:
        controller.heos_manager = heos.manager.HeosDeviceManager()
    controller.heos_manager._all_devices["1234"] = DummyHeos()

    response = await client.get('/heos_device/Dummy/')
    assert response.status_code == 200

    raw_data = await response.get_data()
    data = json.loads(raw_data)

    assert type(data) == dict


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ('/heos_device/Dummy/bla/',
                                     '/heos_device/Test/play/',
                                     '/heos_device/Dummy/Play/',
                                     ))
async def test_get_heos_device_command_invalid(client, command):
    response: quart.wrappers.Response

    if not controller.heos_manager:
        controller.heos_manager = heos.manager.HeosDeviceManager()
    controller.heos_manager._all_devices["1234"] = DummyHeos()

    response = await client.get(command)
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ('/heos_device/Dummy/play/',
                                     '/heos_device/Dummy/pause/',
                                     '/heos_device/Dummy/stop/',
                                     '/heos_device/Dummy/volume_up/',
                                     '/heos_device/Dummy/volume_down/',
                                     '/heos_device/Dummy/next/',
                                     '/heos_device/Dummy/prev/',
                                     ))
async def test_get_heos_device_command(client, command):
    response: quart.wrappers.Response

    if not controller.heos_manager:
        controller.heos_manager = heos.manager.HeosDeviceManager()

    controller.heos_manager._all_devices["1234"] = DummyHeos()

    response = await client.get(command)
    assert response.status_code == 200
