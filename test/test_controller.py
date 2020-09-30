import json

import pytest
import quart
import quart.flask_patch
import quart.testing

import controller
from controller import app as app_for_testing, convert_to_dict


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
    assert 'network_devices' in json_data


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
