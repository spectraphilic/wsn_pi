import cbor2
import pprint


SENSORS = {
    0: [('tst', 0)],
    1: [('serial', 0)],
    2: [('name', 0)],
    3: [('frame', 0)],
    210: [('bme_tc', -2), ('bme_hum', -2), ('bme_pres', 2)],
    211: [('mlx_object', -2), ('mlx_ambient', -2)],
    219: [('sht_tc', -2), ('sht_hum', -2)],
    220: [('channel_f1', 0), ('channel_f2', 0), ('channel_f3', 0),
          ('channel_f4', 0), ('channel_f5', 0), ('channel_f6', 0),
          ('channel_f7', 0), ('channel_f8', 0), ('channel_clear', 0),
          ('channel_nir', 0)],
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
    data = '9f001a611d2a3b011b004b12002e1540190260030318dc0405080a186c18480c0d131518d219091c19182419037b18d319095f19096318db19096c19196fff'
    data = bytes.fromhex(data)
    frame = parse_frame(data)
    pprint.pprint(frame)
