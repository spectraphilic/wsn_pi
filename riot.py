import cbor2
import pprint


SENSORS = {
    0: [('tst', 0)],
    1: [('serial', 0)],
    2: [('name', 0)],
    3: [('frame', 0)],
    210: [('bme_tc', -2), ('bme_hum', -2), ('bme_pres', 2)],
    219: [('sht_tc', -2), ('sht_hum', -2)],
}


def parse_frame(data):
    data = cbor2.loads(data)
    n = len(data)

    frame = {}
    i = 0
    while i < n:
        key = data[i]
        i += 1
        for name, scale in SENSORS[key]:
            value = data[i]
            i += 1
            frame[name] = value * (10 ** scale)

    return frame


if __name__ == '__main__':
    data = '9f001a611ceaa2011b004b12002e1540190260030018d219095819158d19037d18db1909a61916fdff'
    data = bytes.fromhex(data)
    frame = parse_frame(data)
    pprint.pprint(frame)
