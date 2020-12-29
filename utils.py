from configparser import RawConfigParser as ConfigParser
from digi.xbee import devices


def get_config(name):
    config_parser = ConfigParser()
    config_parser.read('config.ini')

    config = {}
    for section in ['global', name]:
        try:
            config.update(dict(config_parser[section]))
        except KeyError:
            pass

    return config


def get_device(port, bauds):
    # Auto discover protocol
    device = devices.XBeeDevice(port, bauds)
    try:
        device.open()
        protocol = device.get_protocol()
    finally:
        device.close()

    # Load device class
    device = {
        0: devices.ZigBeeDevice, # ZigBee
        1: devices.Raw802Device, # 802.15.4
        3: devices.DigiMeshDevice, # DigiMesh
    }[protocol.code]

    # Ok
    return device(port, bauds)


def get_address(remote):
    """
    Return address from remote device.
    """
    address = remote.get_64bit_addr()
    if address == address.UNKNOWN_ADDRESS:
        address = remote.get_16bit_addr()

    return address
