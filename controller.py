import json

import quart
import upnpy

app = quart.Quart("HEOS Communication Server")
app.secret_key = "HeosCommunication_ChangeThisKeyForInstallation"

found_heos_devices = list()


@app.before_first_request
async def scan_for_devices():
    global found_heos_devices
    found_heos_devices = list()

    upnp = upnpy.UPnP()
    devices = upnp.discover()
    for device in devices:
        if b"urn:schemas-denon-com:device:AiosServices:1" in device.description:
            append_device = {
                'name': device.friendly_name,
                'host': device.host,
                'port': device.port,
                'type': device.type_,
                'base_url': device.base_url,
                'services': []
            }
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

    return found_heos_devices


@app.route('/')
async def main():
    return json.dumps({
        'network_devices': quart.request.url_root + "devices/",
        'heos-devices': quart.request.url_root + "heos_devices/",
    }), 200, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/devices/')
async def get_devices():
    return json.dumps(found_heos_devices), 200, {'Content-Type': 'application/json; charset=utf-8'}




@app.route('/heos_devices/')
async def get_heos_devices():
    result = []
    return json.dumps(result), 200, {'Content-Type': 'application/json; charset=utf-8'}


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
