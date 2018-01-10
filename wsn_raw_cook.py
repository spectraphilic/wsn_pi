# Standard Library
import base64
import copy
import json
import struct
import time

from serial import Serial
from xbee import XBee

import mq
import parse_frame
import control


DBNAME = 'var/raw_cook.json'

class Consumer(mq.MQ):

    name = 'wsn_raw_cook'

    def sub_to(self):
        return ('wsn_raw', 'fanout', self.name, self.handle_message)

    def pub_to(self):
        return ('wsn_data', 'fanout', '')

    def update_db(self, source_addr_long, **kw):
        assert type(source_addr_long) is int
        global db
        db_new = copy.deepcopy(db)
        db_new.setdefault(source_addr_long, {}).update(kw)
        if db != db_new:
            db = db_new
            with open(DBNAME, 'w') as db_file:
                json.dump(db, db_file, indent=2)

    def handle_rx(self, body):
        """"
        {'source_addr_long': '\x00\x13\xa2\x00Aj\x07#',
         'rf_data': "<=>\x06\x1eb'g\x05|\x10T\x13#\xc3{\xa8\n\xf3Y4b\xc8\x00\x00PA33\xabA\x00\x00\x00\x00",
         'source_addr': '\xff\xfe',
         'id': 'rx',
         'options': '\xc2'}
        """
        source_addr_long = body['source_addr_long']

        # Skip source_addr, id and options
        frame = parse_frame.parse_frame(body['rf_data'])[0]
        frame['received'] = body['received']
        frame['source_addr_long'] = source_addr_long
        self.publish(frame)

        # Sending frames section
        kw = {}
        bauds = int(self.config.get('bauds', 9600))
        address = struct.pack(">Q", source_addr_long)
        tst = int(time.time())

        # RSSI
        name = 'rssi_tst'
        threshold = 3300 # 55 min
        #threshold = 30 # 30s for testing
        if (tst - threshold) > db.get(source_addr_long, {}).get(name, 0):
            kw[name] = tst
            with Serial('/dev/serial0', bauds) as serial:
                xbee = XBee(serial)
                control.remote_at(xbee, address, command='DB')
            self.info('Asked for rssi')

        # Sync time
        name = 'cmd_time'
        threshold = 3300 # 55 min
        #threshold = 30 # 30s for testing
        kw = {}
        tst = int(time.time())
        if (tst - threshold) > db.get(source_addr_long, {}).get(name, 0):
            kw[name] = tst
            data = 'time %d' % tst
            with Serial('/dev/serial0', bauds) as serial:
                xbee = XBee(serial)
                xbee.tx_long_addr(dest_addr=address, data=data)
            self.info('Sent "time" command')

        # Update db
        self.update_db(source_addr_long, serial=frame['serial'], **kw)

    def handle_remote_at_response(self, body):
        """
        {'command': b'DB',
         'body_id': b'\x06',
         'id': 'remote_at_response',
         'parameter': b'6',
         'source_addr': b'\xff\xfe',
         'source_addr_long': b'\x00\x13\xa2\x00A\x05\xd8\xcf',
         'status': b'\x00'}
        """
        if body['status'] != b'\x00':
            self.warning('REMOTE_AT Response failed', body)
            return

        if body['command'] != b'DB':
            self.warning('UNEXPECTED command %s', body['command'])
            return

        source_addr_long = body['source_addr_long']
        received = body['received']
        self.publish({
            'received': received,
            'source_addr_long': source_addr_long,
            'serial': db.get(source_addr_long, {}).get('serial'),
            'rssi': - struct.unpack('B', body['parameter'])[0],
        })

        # Update db
        self.update_db(source_addr_long, rssi_tst=received)

    def handle_message(self, body):
        # Decode
        for k in body.keys():
            if k not in ('id', 'received'):
                body[k] = base64.b64decode(body[k])

        source_addr_long = struct.unpack(">Q", body['source_addr_long'])[0]
        body['source_addr_long'] = source_addr_long

        # Handle
        frame_type = body['id']
        handler = {
            'rx': self.handle_rx,
            'remote_at_response': self.handle_remote_at_response,
        }.get(frame_type)

        if handler is None:
            self.warning('UNEXPECTED ID %s', frame_type)
            return

        handler(body)


if __name__ == '__main__':
    try:
        with open(DBNAME) as db_file:
            db = json.load(db_file)
    except FileNotFoundError:
        db = {}
    else:
        # JSON keys are always strings, but we use ints
        db = {int(key): value for key, value in db.items()}

    with Consumer() as consumer:
        consumer.start()
