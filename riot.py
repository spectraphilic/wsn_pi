import cbor2


SENSORS = {
    0: ('tst', 0),
    1: ('serial', 0),
    2: ('name', 0),
    3: ('frame', 0),
    130: ('bme_tc', -2),
    131: ('bme_hum', -2),
    137: ('bme_pres', 2),
}


def parse_frame(data):
    data = cbor2.loads(data)

    frame = {}
    for i in range(0, len(data), 2):
        key = data[i]
        value = data[i+1]
        name, scale = SENSORS[key]
        frame[name] = value * (10 ** scale)

    return frame
