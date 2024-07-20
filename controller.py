import asyncio
import json

import quart
import upnpy

import heos
import heos.manager

app = quart.Quart("HEOS Communication Server", static_url_path='')
app.secret_key = "HeosCommunication_ChangeThisKeyForInstallation"

found_heos_devices = list()
heos_manager: heos.manager.HeosDeviceManager = None


@app.before_serving
async def _start_server():
    global heos_manager
    heos_manager = heos.manager.HeosDeviceManager()

    loop = asyncio.get_event_loop()
    loop.create_task(scan_for_devices(1))
    await asyncio.sleep(1)


@app.after_serving
async def _shut_down():
    global heos_manager
    await heos_manager.stop_watch_events()

    await asyncio.sleep(2)


async def scan_for_devices(timeout=2):
    global found_heos_devices

    upnp = upnpy.UPnP()
    devices = upnp.discover(delay=timeout)
    found_ips = list()
    for device in devices:
        if b"urn:schemas-denon-com:device:AiosServices:1" in device.description:
            if not any(heos_dev['name'] == device.friendly_name for heos_dev in found_heos_devices):
                append_device = {
                    'name': device.friendly_name,
                    'host': device.host,
                    'port': device.port,
                    'type': device.type_,
                    'base_url': device.base_url,
                    'services': []
                }
                found_ips.append(device.host)
                for service in device.get_services():
                    append_device['services'].append(
                        {
                            'service': service.service,
                            'type': service.type_,
                            'version': service.version,
                            'base_url': service.base_url,
                            'control_url': service.control_url
                        })
                found_heos_devices.append(append_device)
    global heos_manager
    if heos_manager:
        await heos_manager.initialize(found_ips)
        await heos_manager.start_watch_events()


@app.route('/')
async def main():
    return await app.send_static_file('index.html')


@app.route('/api/')
async def get_api():
    global heos_manager

    if not heos_manager:
        heos_manager = heos.manager.HeosDeviceManager()

    devicecommand = dict()
    for device in heos_manager.get_all_devices():
        commands = list()
        commands.append(quart.request.url_root[:-4] + "heos_device/" + device.name + "/")
        commands.append(quart.request.url_root[:-4] + "heos_device/" + device.name + "/play/")
        commands.append(quart.request.url_root[:-4] + "heos_device/" + device.name + "/pause/")
        commands.append(quart.request.url_root[:-4] + "heos_device/" + device.name + "/stop/")
        commands.append(quart.request.url_root[:-4] + "heos_device/" + device.name + "/volume_up/")
        commands.append(quart.request.url_root[:-4] + "heos_device/" + device.name + "/volume_down/")
        commands.append(quart.request.url_root[:-4] + "heos_device/" + device.name + "/next/")
        commands.append(quart.request.url_root[:-4] + "heos_device/" + device.name + "/prev/")
        devicecommand[device.name] = commands

    sourcecommand = dict()
    for source in heos_manager.get_all_sources():
        commands = list()
        commands.append(quart.request.url_root[:-4] + "heos_source/" + str(source.sid) + "/")
        sourcecommand[source.sid] = commands

    return json.dumps({
        'network-devices': quart.request.url_root[:-4] + "devices/",
        'heos-devices': quart.request.url_root[:-4] + "heos_devices/",
        'heos-sources': quart.request.url_root[:-4] + "heos_sources/",
        'heos-events-page': quart.request.url_root[:-4] + "event_test/",
        'heos-device': devicecommand,
        'heos-source': sourcecommand,
    }), 200, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/devices/')
async def get_devices():
    global found_heos_devices
    return json.dumps(found_heos_devices), 200, {'Content-Type': 'application/json; charset=utf-8'}


def convert_to_dict(obj):
    obj_dict = dict()
    for key, value in obj.__class__.__dict__.items():
        if not key.startswith("_") and not callable(value):
            obj_dict[key] = value
    for key, value in obj.__dict__.items():
        if not key.startswith("_") and not callable(value):
            obj_dict[key] = value
    return obj_dict


@app.route('/heos_devices/')
async def get_heos_devices():
    global heos_manager

    if not heos_manager:
        heos_manager = heos.manager.HeosDeviceManager()

    result = heos_manager.get_all_devices()
    return json.dumps(result, default=convert_to_dict), 200, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/heos_device/<name>/')
async def get_heos_device(name):
    result = heos_manager.get_device_by_name(name)
    if result:
        return json.dumps(result, default=convert_to_dict), 200, {'Content-Type': 'application/json; charset=utf-8'}
    else:
        return b'Device not found.', 404

@app.route('/heos_device/<name>/volume/')
async def get_volume(name):
    device = heos_manager.get_device_by_name(name)
    if not device:
        return b'Device not found.', 404

    return str(device.volume), 200

@app.route('/heos_device/<name>/<command>/')
@app.route('/heos_device/<name>/<command>/<param>/')
async def send_heos_command(name, command):
    device = heos_manager.get_device_by_name(name)
    if not device:
        return b'Device not found.', 404

    if command not in ('play', 'pause', 'stop', 'volume_up', 'volume_down', 'next', 'prev'):
        return b'Invalid command.', 404

    successful = False
    if command in ('play', 'pause', 'stop'):
        successful = await device.set_play_state(command)
    elif command in ('volume_up', 'volume_down'):
        successful = await device.set_volume(device.volume + 2 if command == 'volume_up' else device.volume - 2)
    elif command == 'next':
        successful = await device.next_track()
    elif command == 'prev':
        successful = await device.prev_track()

    return json.dumps({
        'successful': successful
    }), 200, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/heos_sources/')
async def get_heos_sources():
    result = heos_manager.get_all_sources()
    if result:
        return json.dumps(result, default=convert_to_dict, sort_keys=True), 200, {'Content-Type': 'application/json; charset=utf-8'}
    else:
        return b'No Heos Source found.', 404


@app.route('/heos_source/<int:sid>/')
@app.route('/heos_source/<int:sid>/<path:cid>/')
async def get_heos_source_container(sid: int, cid: str = ""):
    result = heos_manager.get_source_by_id(sid)
    if not result:
        return b'No Heos Source found.', 404

    if cid:
        result = result.get_container(cid)

        if not result:
            return b'No Heos Source container found.', 404

        await result.browse(1)

    return json.dumps(result, default=convert_to_dict), 200, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/event_test/')
async def get_events_dummy_template():
    return await quart.render_template('events_dummy.html')


@app.route('/heos_events/')
async def get_heos_event_stream():
    event_queue = heos.EventQueueManager.get_queue()

    async def send_events():
        while True:
            if not event_queue.empty():
                event = await event_queue.get()
                yield event.encode()

            await asyncio.sleep(0.3)

    response = await quart.make_response(
        send_events(),
        {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Expires': -1,
            'Transfer-Encoding': 'chunked',
        },
    )
    response.timeout = None  # No timeout for this route
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False)
