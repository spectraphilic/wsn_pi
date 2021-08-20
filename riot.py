import cbor2
import collections
import pprint
import sys


Field = collections.namedtuple('Field', ['name', 'scale', 'n'], defaults=[0, 1])

SENSORS = {
    0: [('tst', 0)],
    1: [('serial', 0)],
    2: [('name', 0)],
    3: [('frame', 0)],
    210: [('bme_tc', -2), ('bme_hum', -2), ('bme_pres', 2)],
    211: [('mlx_object', -2), ('mlx_ambient', -2)],
    212: [('tmp_temperature', -2)],
    213: [('vl_distance', 0, 0)],
    219: [('sht_tc', -2), ('sht_hum', -2)],
    220: [('channel_f1', 0), ('channel_f2', 0), ('channel_f3', 0),
          ('channel_f4', 0), ('channel_f5', 0), ('channel_f6', 0),
          ('channel_f7', 0), ('channel_f8', 0), ('channel_clear', 0),
          ('channel_nir', 0)],
    222: [('vcnl_prox', 0), ('vcnl_lux', 0), ('vcnl_white', 0)],
    223: [('veml_lux', -2), ('veml_white', -2), ('veml_als', 0)],
}


class Parser:

    def __init__(self, data):
        self.data = bytes.fromhex(data)
        self.size = len(self.data)
        self.__idx = 0

    def get_frame(self):
        data = cbor2.loads(self.data)
        data = iter(data)

        frame = {}
        while True:
            try:
                key = next(data)
            except StopIteration:
                break

            for field in SENSORS[key]:
                field = Field(*field)
                if field.n == 1:
                    value = next(data)
                    frame[field.name] = value * (10 ** field.scale)
                elif field.n == 0:  # Variable number of values
                    n = next(data)
                    values = [next(data)]
                    for j in range(1, n):
                        values.append(values[-1] + next(data))
                    frame[field.name] = [x * (10 ** field.scale) for x in values]
                else:
                    raise NotImplementedError()

        return frame


if __name__ == '__main__':
    if len(sys.argv) > 1:
        data = sys.argv[1]
    else:
        data = '9f001a611f6e3f011b004b12002e1540190260030018dc1416181f182319010b18ff182d' \
               '18351848185718d21908cd1915f619037c18d31908dd1908ff18db19092119175218d419' \
               '092618de01189419017f18df194a29390725190ce018d50f190566190566190566190566' \
               '190566190566190566190566190566190566190566190566190566190566190566ff'

    parser = Parser(data)
    print('Frame size = ', parser.size)
    frame = parser.get_frame()
    pprint.pprint(frame)
