import ast
import asyncio
import inspect
import json
import re
import telnetlib
import typing

import heos


class HeosEventCallback:
    def __init__(self, name: str, param_names: list = []):
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
        self.volume: int = 0
        self.is_muted = False
        self.repeat = "off"
        self.now_playing = dict()

        if doUpdate:
            loop = asyncio.get_event_loop()
            loop.create_task(self.initialize())

    async def initialize(self):
        await self.update_status()
        await self.update_volume_force()
        await self.update_now_playing()

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
        if volume < 0 or volume > 100:
            return False

        successful, _, _ = await self._send_telnet_message(
            b'heos://player/set_volume?pid=' + str(self.pid).encode() + b'&level=' + str(volume).encode())

        if successful:
            self.volume = volume

        return successful

    async def set_mute(self, is_muted: bool = True):
        successful, _, _ = await self._send_telnet_message(
            b'heos://player/set_mute?pid=' + str(self.pid).encode() + b'&state=' + (b'on' if is_muted else b'off'))

        if successful:
            self.is_muted = is_muted

        return successful

    async def next_track(self):
        successful, _, _ = await self._send_telnet_message(
            b'heos://player/play_next?pid=' + str(self.pid).encode()
        )

        return successful

    async def prev_track(self):
        successful, _, _ = await self._send_telnet_message(
            b'heos://player/play_previous?pid=' + str(self.pid).encode()
        )

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
            self.volume = int(re.search("(?<=&level=)[0-9]+", message).group(0))

        successful, message, payload = await self._send_telnet_message(
            b'heos://player/get_mute?pid=' + str(self.pid).encode())
        if successful:
            self.mute = re.search("(?<=&state=)[a-z]+", message).group(0)

    @HeosEventCallback('player_volume_changed', ['level', 'mute'])
    async def update_volume(self, level, mute):
        self.volume = int(level)
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


class HeosSearchCriteria:

    def __init__(self, ip, sid, data):
        self._ip = ip
        self.sid = sid
        self.scid = data["scid"] if "scid" in data else 0
        self.name = data["name"] if "name" in data else ""
        self.allow_wildcard = data["wildcard"] == "yes"
        self.is_playable = data["playable"] == "yes" if "playable" in data else False
        self.cid = data["cid"] if "cid" in data else 0


class HeosSourceContainer:

    def __init__(self, ip, sid, data):
        self._ip = ip
        self.sid = data["sid"] if "sid" in data else sid
        self.cid = data["cid"] if "cid" in data else 0
        self.mid = data["mid"] if "mid" in data else 0
        self.is_container = data["container"] == "yes" if "container" in data else True
        self.is_playable = data["playable"] == "yes" if "playable" in data else False
        self.type = data["type"]
        self.name = data["name"]
        self.container = list()
        self.search_criteria = list()

    async def _send_telnet_message(self, command: bytes) -> (bool, str, dict):
        data = await HeosDeviceManager.send_telnet_message(self._ip, command)
        successful = data["heos"]["result"] == 'success'
        if "payload" in data:
            return successful, data["heos"]["message"], data["payload"]
        else:
            return successful, data["heos"]["message"], {}

    async def get_search_criteria(self):
        successful, message, payload = await self._send_telnet_message(
            b'heos://browse/get_search_criteria?sid=' + str(self.sid).encode()
        )

        if successful:
            self.search_criteria = list()
            for criteria in payload:
                self.search_criteria.append(HeosSearchCriteria(self._ip, self.sid, criteria))

    async def browse(self, recursion_level=0):
        successful, message, payload = False, "", list()
        if self.cid:
            successful, message, payload = await self._send_telnet_message(
                b'heos://browse/browse?sid=' + str(self.sid).encode()
                + b'&cid=' + str(self.cid).encode()
                + b'&range=0,100'
            )
        else:
            successful, message, payload = await self._send_telnet_message(
                b'heos://browse/browse?sid=' + str(self.sid).encode()
            )

        if successful:
            self.container = list()
            for container in payload:
                new_container = HeosSourceContainer(self._ip, self.sid, container)
                self.container.append(new_container)
                if recursion_level > 0:
                    await new_container.browse(recursion_level - 1)


class HeosSource:

    def __init__(self, ip, data):
        self._ip = ip
        self.name = data["name"]
        self.type = data["type"]
        self.sid = data["sid"]
        self.available = data["available"]
        self.username = data["service_username"] if "service_username" in data else ""
        self.container = list()
        self.search_criteria = list()

    async def initialize(self):
        await self.get_root_container()
        await self.get_search_criteria()

    async def _send_telnet_message(self, command: bytes) -> (bool, str, dict):
        data = await HeosDeviceManager.send_telnet_message(self._ip, command)
        successful = data["heos"]["result"] == 'success'
        if "payload" in data:
            return successful, data["heos"]["message"], data["payload"]
        else:
            return successful, data["heos"]["message"], {}

    async def refresh(self):
        successful, message, payload = await self._send_telnet_message(
            b' heos://browse/get_source_info?sid=' + str(self.sid).encode())

        if successful:
            self.available = payload[0]["available"]

    async def get_search_criteria(self):
        successful, message, payload = await self._send_telnet_message(
            b'heos://browse/get_search_criteria?sid=' + str(self.sid).encode()
        )

        if successful:
            self.search_criteria = list()
            for criteria in payload:
                self.search_criteria.append(HeosSearchCriteria(self._ip, self.sid, criteria))


    async def get_root_container(self):
        successful, message, payload = await self._send_telnet_message(
            b' heos://browse/browse?sid=' + str(self.sid).encode())

        if successful:
            self.container = list()
            for container in payload:
                new_container = HeosSourceContainer(self._ip, self.sid, container)
                self.container.append(new_container)
                await new_container.browse(0)
                await new_container.get_search_criteria()


class HeosDeviceManager:
    _locks: typing.Dict[str, asyncio.Lock] = dict()

    def __init__(self):
        self._all_devices: typing.Dict[str, HeosDevice] = dict()
        self._all_sources: typing.Dict[int, HeosSource] = dict()
        self.watch_enabled = False
        self.event_telnet_connection: telnetlib.Telnet

    async def initialize(self, list_of_ips):
        await self._scan_for_devices(list_of_ips)
        await self._scan_for_sources(list_of_ips)

    @staticmethod
    async def send_telnet_message(ip, command: bytes) -> dict:
        if ip not in HeosDeviceManager._locks:
            HeosDeviceManager._locks[ip] = asyncio.Lock()

        async with HeosDeviceManager._locks[ip]:
            tn = telnetlib.Telnet(ip, 1255)
            tn.write(command + b"\n")

            message = b''
            while True:
                message += tn.read_until(b"}")
                if message:
                    try:
                        data = json.loads(message.decode('utf-8'))

                        # reset message because real answer was not fetched
                        if data["heos"]["message"].startswith("command under process"):
                            message = b''
                        else:
                            return data

                    except json.JSONDecodeError:
                        pass

                    except UnicodeDecodeError:
                        pass

    async def _scan_for_devices(self, list_of_ips):
        for ip in list_of_ips:
            data = await self.send_telnet_message(ip, b'heos://player/get_players')
            for device in data["payload"]:
                if not device["pid"] in self._all_devices:
                    new_device = HeosDevice(device)
                    self._all_devices[new_device.pid] = new_device
                    await new_device.initialize()

    async def _scan_for_sources(self, list_of_ips):
        for ip in list_of_ips:
            data = await self.send_telnet_message(ip, b'heos://browse/get_music_sources')
            for source in data["payload"]:
                if not source["sid"] in self._all_sources:
                    new_source = HeosSource(ip, source)
                    self._all_sources[new_source.sid] = new_source
                    await new_source.initialize()

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

    def get_all_sources(self) -> typing.List[HeosSource]:
        if not self._all_sources:
            return list()

        return list(self._all_sources.values())
