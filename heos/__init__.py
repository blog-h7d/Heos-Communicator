import asyncio
import typing


class ServerHeosEvent:
    def __init__(self, data, event: str = 'event', identifier: int = 1, retry: int = 1):
        self.data = data
        self.event = event
        self.id = identifier
        self.retry = retry

    def encode(self) -> bytes:
        message = f"Event: {self.event}"
        message += f"\ndata: {self.data}"
        # message += f"\nid: {self.id}"
        # message += f"\nretry: {self.retry}"
        message += "\n\n"
        return message.encode('utf-8')


class EventQueueManager:
    _queues = list()  # type: typing.List[asyncio.Queue]

    @staticmethod
    def add_event(event: ServerHeosEvent):
        for queue in EventQueueManager._queues:  # type: asyncio.Queue
            if queue.full():
                EventQueueManager._queues.remove(queue)
            else:
                queue.put_nowait(event)

    @staticmethod
    def get_queue() -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=2048)
        EventQueueManager._queues.append(queue)
        return queue
