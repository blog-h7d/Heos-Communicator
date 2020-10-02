import typing

import heos.manager


class HeosSearchCriteria:

    def __init__(self, ip, parent, data):
        self._ip = ip
        self._parent = parent
        self.scid = data["scid"] if "scid" in data else 0
        self.name = data["name"] if "name" in data else ""
        self.allow_wildcard = data["wildcard"] == "yes"
        self.is_playable = data["playable"] == "yes" if "playable" in data else False
        self.cid = data["cid"] if "cid" in data else 0


class HeosSourceBase:
    def __init__(self, ip, parent, data):
        self._ip = ip
        self._parent: HeosSourceBase = parent
        self._id = self._get_id_tuple(data)[1]

        self.type = data["type"]
        self.name = data["name"]

        self.children: typing.Dict[str, HeosSourceBase] = dict()
        self.search_criteria: typing.List[HeosSearchCriteria] = list()

    async def initialize(self):
        raise NotImplementedError

    async def _send_telnet_message(self, command: bytes) -> (bool, str, dict):
        data = await heos.manager.HeosDeviceManager.send_telnet_message(self._ip, command)
        successful = data["heos"]["result"] == 'success'
        if "payload" in data:
            return successful, data["heos"]["message"], data["payload"]
        else:
            return successful, data["heos"]["message"], {}

    @staticmethod
    def _get_id_tuple(json_data) -> (type, str):

        if "mid" in json_data:
            return HeosSourceMusic, "mid: " + str(json_data["mid"])

        if "cid" in json_data:
            return HeosSourceContainer, "cid: " + str(json_data["cid"])

        if "sid" in json_data:
            return HeosSource, "sid: " + str(json_data["sid"])

        raise AttributeError("no valid data for Heos Source")

    def _get_cid_from_parent(self):
        if self._parent:
            if isinstance(self._parent, HeosSourceContainer):
                return self._parent.cid

            return self._parent._get_cid_from_parent()

    def _get_sid_from_parent(self):
        if self._parent:
            if isinstance(self._parent, HeosSource):
                return self._parent.sid

            return self._parent._get_sid_from_parent()

    def get_container(self, cid: str):
        for child in self.children.values():
            found = child.get_container(cid)
            if found:
                return found

    async def browse(self, recursion_level=0):
        successful, message, payload = await self._send_telnet_message(
            self._get_browse_command())

        if successful:
            self.children = dict()
            for child in payload:
                child_type, child_id = self._get_id_tuple(child)
                new_child = child_type(self._ip, self, child)  # type: HeosSourceBase
                self.children[child_id] = new_child

                await new_child.initialize()
                if recursion_level > 0:
                    await new_child.browse(recursion_level - 1)

    def _get_browse_command(self):
        raise NotImplementedError


class HeosSourceMusic(HeosSourceBase):

    def __init__(self, ip, parent, data):
        super().__init__(ip, parent, data)

        self.mid = data["mid"]

    async def initialize(self):
        pass

    def get_container(self, cid: str):
        pass

    async def _get_browse_command(self):
        pass

    async def browse(self, recursion_level=0):
        pass


class HeosSourceContainer(HeosSourceBase):

    def __init__(self, ip, parent, data):
        super().__init__(ip, parent, data)
        self.cid = data["cid"].strip()
        self.is_container = data["container"] == "yes" if "container" in data else True
        self.is_playable = data["playable"] == "yes" if "playable" in data else False

        self._sid = self._get_sid_from_parent()

    async def initialize(self):
        pass

    def get_container(self, cid: str):
        if self.cid == cid:
            return self

        return super().get_container(cid)

    def _get_browse_command(self):
        # TODO: get valid range
        return b'heos://browse/browse?sid=' + str(self._sid).encode() \
               + b'&cid=' + str(self.cid).encode() \
               + b'&range=0,100'

    def _get_cid_from_parent(self):
        return self.cid


class HeosSource(HeosSourceBase):

    def __init__(self, ip, parent, data):
        super().__init__(ip, parent, data)

        self.sid = data["sid"] if "sid" in data else ""
        self.available = data["available"] if "available" in data else ""
        self.username = data["service_username"] if "service_username" in data else ""

    async def initialize(self):
        await self.get_search_criteria()
        if self.sid > 1000:  # no online services
            await self.browse(2)

    async def refresh(self):
        successful, message, payload = await self._send_telnet_message(
            b'heos://browse/get_source_info?sid=' + str(self.sid).encode())

        if successful:
            self.available = payload[0]["available"]

        await self.initialize()

    async def get_search_criteria(self):
        successful, message, payload = await self._send_telnet_message(
            b'heos://browse/get_search_criteria?sid=' + str(self.sid).encode()
        )

        if successful:
            self.search_criteria = list()
            for criteria in payload:
                self.search_criteria.append(HeosSearchCriteria(self._ip, self.sid, criteria))

    def _get_browse_command(self):
        return b'heos://browse/browse?sid=' + str(self.sid).encode()

    def get_source(self, sid: int):
        if int(sid) == self.sid:
            return self

        for (child_type, child) in self.children.items():  # type:(str, HeosSourceBase)
            if child_type[0:3] == "sid":
                return child.get_source(sid)

        return None

    def _get_sid_from_parent(self):
        return self.sid
