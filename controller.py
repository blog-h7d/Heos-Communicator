import asyncio
import json

import quart
import upnpy

import heos.manager

app = quart.Quart("HEOS Communication Server")
app.secret_key = "HeosCommunication_ChangeThisKeyForInstallation"

found_heos_devices = list()
heos_manager: heos.manager.HeosDeviceManager


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

    for device in heos_manager.get_all_devices():
        await device.stop_watcher()

    await asyncio.sleep(2)


async def scan_for_devices(timeout):
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
    await heos_manager.initialize(found_ips)
    await heos_manager.start_watch_events()


@app.route('/')
async def main():
    return json.dumps({
        'network_devices': quart.request.url_root + "devices/",
        'heos-devices': quart.request.url_root + "heos_devices/",
        'heos_events': quart.request.url_root + "heos_events/"
    }), 200, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/devices/')
async def get_devices():
    global found_heos_devices
    return json.dumps(found_heos_devices), 200, {'Content-Type': 'application/json; charset=utf-8'}


def convert_to_dict(obj):
    obj_dict = dict()
    for key, value in obj.__dict__.items():
        if not key.startswith("_"):
            obj_dict[key] = value
    return obj_dict


@app.route('/heos_devices/')
async def get_heos_devices():
    result = heos_manager.get_all_devices()
    return json.dumps(result, default=convert_to_dict), 200, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/event_test/')
async def get_events_dummy_template():
    return await quart.render_template('events_dummy.html')


@app.route('/heos_events/')
async def get_heos_event_stream():
    async def send_events():
        while True:
            if len(heos.manager.data_queue) > 0:
                event = heos.manager.data_queue.pop(0)
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
