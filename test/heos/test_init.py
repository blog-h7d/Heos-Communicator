import pytest

from heos import ServerHeosEvent


def test_server_heos_event_init():
    she = ServerHeosEvent(1)

    assert she.data == 1
    assert she.event == 'event'
    assert she.id == 1
    assert she.retry == 1


@pytest.mark.parametrize('data', ["123", "かんじ", "['a','b']"])
def test_server_heos_event_encode(data):
    she = ServerHeosEvent(data)
    assert she.data == data

    message = she.encode()
    assert data.encode('utf-8') in message
