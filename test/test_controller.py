import pytest
import quart
import quart.flask_patch
import quart.testing

from controller import app as app_for_testing


@pytest.fixture
def client():
    app_for_testing.config['TESTING'] = True

    yield app_for_testing.test_client()


@pytest.mark.asyncio
async def test_main_page_simple(client):
    response: quart.wrappers.Response

    response = await client.get('/')
    assert response.status_code == 200

    data = await response.get_data()
    assert data


