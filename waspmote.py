'''
Script to parse frames from waspmote

Simon Filhol, J. David Ibáñez
'''

# Standard Library
from datetime import datetime, timezone
import struct

from Crypto.Cipher import AES


"""
f - float
j - int16_t
u - uint8_t
w - uint32_t
s - char*
n - Array of int16_t (specially compressed)
"""

SENSORS = {
     15: (b'PA', 'f', ['pa']),
     33: (b'TCB', 'f', ['tcb']),
     35: (b'HUMB', 'f', ['humb']),
     38: (b'LW', 'f', ['lw']),
     52: (b'BAT', 'u', ['bat']),
     53: (b'GPS', 'ff', ['latitude', 'longitude']),
     54: (b'RSSI', 'j', ['rssi']),
     55: (b'MAC', 's', ['mac']),
     62: (b'IN_TEMP', 'f', ['in_temp']),
#    63: (b'ACC', ),
     65: (b'STR', 's', ['str']),
     74: (b'BME_TC', 'f', ['bme_tc']),
     76: (b'BME_HUM', 'f', ['bme_hum']),
     77: (b'BME_PRES', 'f', ['bme_pres']),
     85: (b'TX_PWR', 'u', ['tx_pwr']),
#    89: (b'SPEED_OG', ),
#    90: (b'COURSE_OG', ),
#    91: (b'ALT', ),
    123: (b'TST', 'w', ['tst']),
    200: (b'SDI12_CTD10', 'fff', ['ctd_depth', 'ctd_temp', 'ctd_cond']),
    201: (b'SDI12_DS2_1', 'fff', ['ds2_speed', 'ds2_dir', 'ds2_temp']),
    202: (b'SDI12_DS2_2', 'fff', ['ds2_meridional', 'ds2_zonal', 'ds2_gust']),
    203: (b'DS18B20', 'n', ['ds1820']),
    204: (b'MB73XX', 'ww', ['mb_median', 'mb_sd']),
    206: (b'VOLTS', 'f', ['volts']),
    207: (b'WS100', 'fffuf', ['precip_abs', 'precip_dif', 'precip_int_h', 'precip_type', 'precip_int_min']),
}


def search_frame(data):
    """
    Search the frame starting with the delimiter <=>, return a tuple with:

    - the data found before the delimiter (garbage)
    - the data starting from the delimiter
    """
    # End of data
    if not data:
        return '', ''

    index = data.find(b'<=>')

    # Not found
    if index == -1:
        return data, ''

    if index > 0:
        return data[:index], data[index:]

    return '', data


ciphers = {}
def get_cipher(key):
    if key is None:
        return None

    cipher = ciphers.get(key)
    if cipher is None:
        cipher = AES.new(key, AES.MODE_ECB)
        ciphers[key] = cipher

    return cipher


def parse_frame(line, cipher_key=None):
    """
    Parse the frame starting at the given byte string. We consider that the
    frame start delimeter has already been read.
    """

    if cipher_key is not None and type(cipher_key) is not bytes:
        raise TypeError('cipher_key must be None or bytes, got %s' % type(cipher_key))

    # Start delimiter
    if not line.startswith(b'<=>'):
        print('Warning: expected frame not found')
        return None

    line = line[3:]

    # Frame type
    frame_type = struct.unpack_from("B", line)[0]
    line = line[1:]

    if frame_type & 128: # b7
        print("Warning: text frames not supported (%d)" % frame_type)
        return None

    if frame_type == 96:
        encrypted = True
        v15 = True
    elif 96 < frame_type < 100:
        encrypted = True
        v15 = False
    elif frame_type > 11:
        print("Warning: %d frame type not supported" % frame_type)
        return None
    else:
        encrypted = False
        # 0 -  5 : v12
        # 6 - 11 : v15
        # From 7 to 11 are "Reserved types" in Libellium's lib. But we use the
        # event type, and need to tell apart v12 from v15 (otherwise we cannot
        # know whether the serial number is 32 or 64 bits long).
        v15 = frame_type > 5
        if v15:
            # Discard version
            # From 0 (info) to 5 (low battery). We only use 0 and 2
            frame_type -= 6

        frame = {'type': frame_type}

    # Number of bytes (Binary)
    n = struct.unpack_from("B", line)[0]
    line = line[1:]
    rest = line[n:]
    line = line[:n]

    # Serial id
    if v15:
        serial_id = struct.unpack_from(">Q", line)[0]
        line = line[8:]
    else:
        serial_id = struct.unpack_from(">I", line)[0]
        line = line[4:]

    # Encrypted
    if encrypted:
        if not v15:
            name, line = line.split(b'#', 1)
            name = name.decode()

        cipher = get_cipher(cipher_key)
        if cipher is None:
            print('Warning: encrypted frames not supported because no key provided')
            return None

        line = cipher.decrypt(line)
        frame, _ = parse_frame(line) # _ may contain zeroes
        if frame['serial'] != serial_id:
            print("Warning: serial numbers do not match %d != %d", serial_id, frame['serial'])
            return None

        if not v15 and frame['name'] != name:
            print("Warning: name do not match %s != %s", name, frame['name'])
            return None

        return frame, rest

    # Name
    name, line = line.split(b'#', 1)
    name = name.decode() # bytes to str
    # Sequence
    sequence = struct.unpack_from("B", line)[0]
    line = line[1:] # Payload

    frame['serial'] = serial_id
    frame['frame'] = sequence # Frame sequence
    frame['name'] = name

    while line:
        sensor_id = struct.unpack_from("B", line)[0]
        line = line[1:]
        sensor = SENSORS.get(sensor_id, ())
        if not sensor:
            print("Warning: %d sensor type not supported" % sensor_id)
            return None

        key, form, names = sensor

        for c, name in zip(form, names):
            name = name.lower()
            if c == 'f':
                value = struct.unpack_from("f", line)[0]
                line = line[4:]
            elif c == 'j':
                value = struct.unpack_from("h", line)[0]
                line = line[2:]
            elif c == 'u':
                value = struct.unpack_from("B", line)[0]
                line = line[1:]
            elif c == 'w':
                value = struct.unpack_from("I", line)[0]
                line = line[4:]
            elif c == 'str':
                length = struct.unpack_from("B", line)[0]
                line = line[1:]
                value = line[:length]
                line = line[length:]
            elif c == 'n':
                # Variable list of values (done for the DS18B20 string)
                values = []
                n_values = struct.unpack_from("B", line)[0]
                line = line[1:]
                for j in range(n_values):
                    if j > 0:
                        value = struct.unpack_from("b", line)[0]
                        line = line[1:]
                        if value != -128:
                            value = values[-1] + value
                            values.append(value)
                            continue

                    value = struct.unpack_from("h", line)[0]
                    line = line[2:]
                    values.append(value)

                # DS18B20
                if key == b'DS18B20':
                    #f = lambda x: x if (-100 < x < 100) else None # None if out of range
                    #values = [f(value / 16) for value in values]
                    values = [value / 16 for value in values]

                value = frame.get(name, []) + values

            frame[name] = value

    return frame, rest


def read_wasp_data(f):
    src = f.read()

    while src:
        bad, good = search_frame(src)
        if bad:
            print('Warning: %d bytes of garbage found and discarded' % len(bad))
            print(bad[:50])

        if good:
            aux = parse_frame(good)
            if aux is None:
                break

            frame, src = aux
            yield frame

            # read end of frame: \n
            if src and src[0] == '\n':
                src = src[1:]


def data_to_json(data):
    """
    Adapt the data to the structure expected by Django.
    """
    # Tags
    tags = {}
    for key in 'source_addr_long', 'serial', 'name':
        value = data.pop(key, None)
        if value is not None:
            tags[key] = value

    # Time
    time = data.pop('tst', None)
    if time is None:
        time = data['received']
    time = datetime.fromtimestamp(time, timezone.utc).isoformat()

    return {'tags': tags, 'frames': [{'time': time, 'data': data}]}
