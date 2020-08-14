import json
import telnetlib
import typing


class HeosDevice:

    def __init__(self, data: dict):
        self._pid = data["pid"]
        self._name = data["name"]
        self._model = data["model"]
        self._version = data["version"]
        self._ip = data["ip"]
        self._network = data["network"]
        self._serial = data["serial"]


class HeosDeviceManager:

    def __init__(self):
        self._all_devices: typing.dict[str, HeosDevice] = dict()

    @staticmethod
    def _send_telnet_message(ip, command: str) -> str:
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

    def _scan_for_devices(self, list_of_ips) -> HeosDevice:
        for ip in list_of_ips:
            data = self._send_telnet_message(ip, b"heos://player/get_players")
            for device in data["payload"]:
                if not device["pid"] in self._all_devices:
                    new_device = HeosDevice(device)
                    self._all_devices[device["pid"]] = new_device

