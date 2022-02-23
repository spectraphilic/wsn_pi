import cbor2
import collections
import pprint
import sys


Field = collections.namedtuple('Field', ['name', 'scale', 'n'], defaults=[0, 1])

SENSORS = {
    0: [('source_addr', None)],
    1: [('target_addr', None)],
    2: [('serial', None)],
    3: [('name', None)],
    4: [('frame', None)],
    123: [('tst', None)],
    210: [('bme_tc', -2), ('bme_hum', -2), ('bme_pres', 0)],
    211: [('mlx_object', -2), ('mlx_ambient', -2)],
    212: [('tmp_temperature', -2)],
    213: [('vl_distance', 0, 0)],
    219: [('sht_tc', -2), ('sht_hum', -2)],
    220: [('channel_f1', 0), ('channel_f2', 0), ('channel_f3', 0),
          ('channel_f4', 0), ('channel_f5', 0), ('channel_f6', 0),
          ('channel_f7', 0), ('channel_f8', 0), ('channel_clear', 0),
          ('channel_nir', 0)],
#   221: [('icm_temp', -2),
#         ('icm_acc_x', -2), ('icm_acc_y', -2), ('icm_acc_z', -2),
#         ('icm_mag_x', -2), ('icm_mag_y', -2), ('icm_mag_z', -2),
#         ('icm_gyro_x', -2), ('icm_gyro_y', -2), ('icm_gyro_z', -2)],
    222: [('vcnl_prox', 0), ('vcnl_lux', 0), ('vcnl_white', 0)],
    223: [('veml_lux', -2), ('veml_white', -2), ('veml_als', 0)],
}


class Parser:

    def __init__(self, data):
        if type(data) is str:
            data = bytes.fromhex(data)

        self.data = data
        self.size = len(self.data)
        self.__idx = 0

    def get_frame(self):
        data = cbor2.loads(self.data)
        #pprint.pprint(data)
        data = iter(data)

        get_value = lambda value, scale: value / (10 ** -scale) if scale else value

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
                    frame[field.name] = get_value(value, field.scale)
                elif field.n == 0:  # Variable number of values
                    n = next(data)
                    values = [next(data)]
                    for j in range(1, n):
                        values.append(values[-1] + next(data))
                    frame[field.name] = [get_value(x, field.scale) for x in values]
                else:
                    raise NotImplementedError()

        return frame


def parse_frame(data):
    return Parser(data).get_frame()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        data = sys.argv[1]
    else:
        data = '9f001a6123639b011b004b12002e1540190260030018dc17181f18291830190140190102' \
               '183e18491863187b18d21909501911e01a00015d9d18d319095f19099718db19099e1913' \
               '6d18d419099f18de0118a019017918df192eb01995b719081b18d50f1905540000000000' \
               '000000000000000000ff'

    parser = Parser(data)
    print(f'Frame size = {parser.size}')
    frame = parser.get_frame()
    pprint.pprint(frame)
