from configparser import RawConfigParser as ConfigParser
from digi.xbee import devices


def get_section(config_parser, name, default=None):
    try:
        return dict(config_parser[name])
    except KeyError:
        return None


def get_config(name):
    config_parser = ConfigParser()
    config_parser.read('config.ini')

    section_conf = get_section(config_parser, name)
    if section_conf is None:
        return None

    config = get_section(config_parser, 'global', default={})
    config.update(section_conf)
    return config


def get_device(config):
    port = config.get('port', '/dev/serial0')
    bauds = int(config.get('bauds', 9600))

    device = config.get('device', 'digimesh')
    device = {
        '802': devices.Raw802Device,
        'zigbee': devices.ZigBeeDevice,
        'digimesh': devices.DigiMeshDevice,
    }[device]

    return device(port, bauds)


def get_address(remote):
    """
    Return address from remote device.
    """
    address = remote.get_64bit_addr()
    if address == address.UNKNOWN_ADDRESS:
        address = remote.get_16bit_addr()

    return address


def send_data_async(device, remote, data):
    # 802.15.4
    if isinstance(device, devices.Raw802Device):
        address = get_address(remote)
        if isinstance(address, devices.XBee64BitAddress):
            return device.send_data_async_64(address, data, 0)
        elif isinstance(address, devices.XBee16BitAddress):
            return device.send_data_async_16(address, data, 0)

        raise ValueError(f'Unexpected address type {type(address)}')

    # Zigbee
    if isinstance(device, devices.DigiMeshDevice):
        raise NotImplementedError('Zigbee devices not yet supported')

    # XBee
    if isinstance(device, devices.ZigBeeDevice):
        return device.send_data_async(remote, data, 0)

    raise TypeError(f'Unexpected device type {type(device)}')
