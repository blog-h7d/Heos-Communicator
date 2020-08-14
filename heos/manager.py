import asyncio
import json
import telnetlib
import typing


class HeosDevice:

    def __init__(self, data: dict):
        self.pid = data["pid"]
        self.name = data["name"]
        self.model = data["model"]
        self.version = data["version"]
        self.ip = data["ip"]
        self.network = data["network"]
        self.serial = data["serial"]

        loop = asyncio.get_event_loop()
        loop.create_task(self._ping())

    async def _ping(self):
        while True:
            await asyncio.sleep(5)
            await self._send_telnet_message(b'heos://system/heart_beat')

    async def update_status(self):
        pass

    async def _send_telnet_message(self, command: bytes) -> (bool, str, dict):
        data = await HeosDeviceManager.send_telnet_message(self._ip, command)
        successful = data["result"] == 'success'
        if "payload" in data:
            return successful, data["message"], data["payload"]
        else:
            return successful, data["message"], {}


class HeosDeviceManager:
    _locks: typing.Dict[str, asyncio.Lock] = dict()

    def __init__(self):
        self._all_devices: typing.Dict[str, HeosDevice] = dict()

    async def initialize(self, list_of_ips):
        await self._scan_for_devices(list_of_ips)

    @staticmethod
    async def send_telnet_message(ip, command: bytes) -> dict:
        if ip not in HeosDeviceManager._locks:
            HeosDeviceManager._locks[ip] = asyncio.Lock()

        async with HeosDeviceManager._locks[ip]:
            tn = telnetlib.Telnet(ip, 1255)
            tn.write(command + b"\n")
            message = b''
            while True:
                message += tn.read_some()
                if message:
                    try:
                        data = json.loads(message.decode('utf-8'))
                        return data
                    except json.JSONDecodeError:
                        pass
                    except UnicodeDecodeError:
                        pass

    async def _scan_for_devices(self, list_of_ips):
        for ip in list_of_ips:
            data = await self.send_telnet_message(ip, b"heos://player/get_players")
            for device in data["payload"]:
                if not device["pid"] in self._all_devices:
                    new_device = HeosDevice(device)
                    self._all_devices[device["pid"]] = new_device

    def get_all_devices(self) -> typing.List[HeosDevice]:
        if not self._all_devices:
            return list()

        return list(self._all_devices.values())
