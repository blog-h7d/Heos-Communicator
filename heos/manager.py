import ast
import asyncio
import inspect
import json
import re
import telnetlib
import typing

import heos


class HeosEventCallback:
    def __init__(self, name: str, param_names: dict = []):
        self.name = name
        self.param_names = param_names

    def __call__(self, func, *args, **kwargs):
        def new_func(*args, **kwargs):
            return func(*args, **kwargs)

        return new_func


class HeosDevice:

    def __init__(self, data: dict, doUpdate=True):
        self.pid = int(data["pid"])
        self.name = data["name"]
        self.model = data["model"]
        self.version = data["version"]
        self.ip = data["ip"]
        self.network = data["network"]
        self.serial = data["serial"]
        self.play_state = 'stop'
        self.volume = 0
        self.mute = "off"
        self.repeat = "off"
        self.now_playing = dict()

        if doUpdate:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.update_status())
            loop.run_until_complete(self.update_volume_force())
            loop.run_until_complete(self.update_now_playing())

    async def _send_telnet_message(self, command: bytes) -> (bool, str, dict):
        data = await HeosDeviceManager.send_telnet_message(self.ip, command)
        successful = data["heos"]["result"] == 'success'
        if "payload" in data:
            return successful, data["heos"]["message"], data["payload"]
        else:
            return successful, data["heos"]["message"], {}

    async def _ping(self):
        successful, _, _ = await self._send_telnet_message(b'heos://system/heart_beat')
        return successful

    async def set_play_state(self, play_state: str) -> bool:
        if play_state not in ('play', 'pause', 'stop'):
            return False

        successful, _, _ = await self._send_telnet_message(
            b'heos://player/set_play_state?pid=' + str(self.pid).encode() + b'&state=' + play_state.encode())

        if successful:
            self.play_state = play_state

        return successful

    async def set_volume(self, volume: int):
        if volume < 0 or valume > 100:
            return False

        successful, _, _ = await self._send_telnet_message(
            b'heos://player/set_volume?pid=' + str(self.pid).encode() + b'&level=' + str(volume).encode())

        if successful:
            self.volume = volume

        return successful

    @HeosEventCallback('player_state_changed')
    async def update_status(self):
        successful, message, payload = await self._send_telnet_message(
            b'heos://player/get_play_state?pid=' + str(self.pid).encode())
        if successful:
            self.play_state = re.search("(?<=&state=)[a-z]+", message).group(0)

    async def update_volume_force(self):
        successful, message, payload = await self._send_telnet_message(
            b'heos://player/get_volume?pid=' + str(self.pid).encode())
        if successful:
            self.volume = re.search("(?<=&level=)[0-9]+", message).group(0)

        successful, message, payload = await self._send_telnet_message(
            b'heos://player/get_mute?pid=' + str(self.pid).encode())
        if successful:
            self.mute = re.search("(?<=&state=)[a-z]+", message).group(0)

    @HeosEventCallback('player_volume_changed', ['level', 'mute'])
    async def update_volume(self, level, mute):
        self.volume = level
        self.mute = mute

    @HeosEventCallback('player_now_playing_changed')
    async def update_now_playing(self):
        successful, message, payload = await self._send_telnet_message(
            b'heos://player//get_now_playing_media?pid=' + str(self.pid).encode())
        if successful:
            self.now_playing = payload

    @HeosEventCallback('player_now_playing_progress', ['cur_pos', 'duration'])
    async def update_now_playing_progress(self, cur_pos, duration):
        self.now_playing["cur_pos"] = cur_pos
        self.now_playing["duration"] = duration

    async def update_repeat_mode_force(self):
        successful, message, payload = await self._send_telnet_message(
            b'heos://player//get_play_mode?pid=' + str(self.pid).encode())
        if successful:
            self.repeat = re.search("(?<=&repeat=)[a-z_]+", message).group(0)

    @HeosEventCallback('repeat_mode_changed', ['repeat', ])
    async def update_repeat_mode(self, repeat):
        self.repeat = repeat


class HeosDeviceManager:
    _locks: typing.Dict[str, asyncio.Lock] = dict()

    def __init__(self):
        self._all_devices: typing.Dict[str, HeosDevice] = dict()
        self.watch_enabled = False
        self.event_telnet_connection: telnetlib.Telnet

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
                    self._all_devices[new_device.pid] = new_device
                    await new_device.start_watcher()

    async def _filter_response_for_event(self) -> dict:
        tn = self.event_telnet_connection
        message = b''
        while True:
            message += tn.read_until(b'}', 0.1)
            if message:
                try:
                    data = json.loads(message.decode('utf-8'))
                    return data
                except json.JSONDecodeError:
                    pass
                except UnicodeDecodeError:
                    pass
            await asyncio.sleep(0.1)

    async def start_watch_events(self):
        if not self._all_devices or self.watch_enabled:
            return

        self.watch_enabled = True

        ip = self.get_all_devices()[0].ip
        self.event_telnet_connection = telnetlib.Telnet(ip, 1255)
        command = b'heos://system/register_for_change_events?enable=on'
        self.event_telnet_connection.write(command + b"\n")
        await self._filter_response_for_event()

        loop = asyncio.get_event_loop()
        loop.create_task(self._watch_events())

    async def stop_watch_events(self):
        self.watch_enabled = False

    async def _watch_events(self):
        heos_functions = self.get_heos_decorators()

        while self.watch_enabled:
            response = await self._filter_response_for_event()
            command = response["heos"]["command"]  # type:str
            if command.startswith("event/"):
                event = command[6:]
                message = ""
                if "message" in response["heos"]:
                    message = response["heos"]["message"]

                heos.EventQueueManager.add_event(heos.ServerHeosEvent({
                    "command": command,
                    "event": event,
                    "message": message,
                    "full": response
                }))

                for name, func in heos_functions.items():
                    if func[0]["event"] == event:
                        pid = int(re.search("(?<=pid=)-?[a-z0-9]+", message).group(0))
                        if pid and pid in self._all_devices:

                            param_list = list()
                            for param in func[0]["params"]:
                                value = re.search("(?<=" + param + "=)[a-z0-9_]+", message).group(0)
                                param_list.append(value)

                            func = getattr(self._all_devices[int(pid)], name)
                            await func(*param_list)

            await asyncio.sleep(0.1)

    @staticmethod
    def get_heos_decorators(cls=HeosDevice):
        target = cls
        decorators = {}

        def visit_FunctionDef(node):
            decorators[node.name] = []
            for n in node.decorator_list:
                name = ''
                if isinstance(n, ast.Call):
                    name = n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id
                if name in ('HeosEventCallback',):
                    params = list()
                    if len(n.args) == 2:
                        for val in n.args[1].elts:
                            params.append(val.value)

                    decorators[node.name].append({
                        "name": name,
                        "event": n.args[0].value,
                        "params": params
                    })

            if not decorators[node.name]:
                decorators.pop(node.name)

        node_iter = ast.NodeVisitor()
        node_iter.visit_AsyncFunctionDef = visit_FunctionDef
        node_iter.visit(ast.parse(inspect.getsource(target)))

        return decorators

    def get_all_devices(self) -> typing.List[HeosDevice]:
        if not self._all_devices:
            return list()

        return list(self._all_devices.values())

    def get_device_by_name(self, name) -> HeosDevice:
        for device in self._all_devices.values():  # type: HeosDevice
            if device.name == name:
                return device
