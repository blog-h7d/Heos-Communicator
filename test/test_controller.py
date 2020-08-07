import pytest
import json
import quart
import quart.flask_patch
import quart.testing

import controller
from controller import app as app_for_testing


@pytest.fixture
def client():
    app_for_testing.config['TESTING'] = True

    yield app_for_testing.test_client()


@pytest.mark.asyncio
@pytest.mark.device_needed
async def test_scan_for_devices():
    found = await controller.scan_for_devices()
    assert found


@pytest.mark.asyncio
async def test_main_page_simple(client):
    response: quart.wrappers.Response

    response = await client.get('/')
    assert response.status_code == 200

    data = await response.get_data()
    assert data


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
