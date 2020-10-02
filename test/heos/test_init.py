import pytest
import asyncio

from heos import ServerHeosEvent, EventQueueManager


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


@pytest.mark.asyncio
async def test_event_queue_manager_get_queue():
    queue = EventQueueManager.get_queue()
    assert queue in EventQueueManager._queues
    assert queue.empty()

    EventQueueManager.add_event(ServerHeosEvent("Test"))
    assert not queue.empty()

    event = await queue.get()
    assert event
    assert event.data == "Test"

    EventQueueManager._queues.remove(queue)


@pytest.mark.asyncio
async def test_event_queue_full():
    queue = EventQueueManager.get_queue()
    assert queue in EventQueueManager._queues

    for i in range(0, 2048):
        EventQueueManager.add_event(ServerHeosEvent(i))

    assert queue.full()

    EventQueueManager.add_event(ServerHeosEvent("full"))

    await asyncio.sleep(1)

    assert queue not in EventQueueManager._queues

