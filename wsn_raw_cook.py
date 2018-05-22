# Standard Library
import base64
import struct
import time

from serial import Serial
from xbee import DigiMesh

import mq
import parse_frame
import control


EVENT_FRAME = 2 # Used to signal boot


class Consumer(mq.MQ):

    name = 'wsn_raw_cook'
    db_name = 'var/raw_cook.json' 

    def sub_to(self):
        return ('wsn_raw', 'fanout', self.name, self.handle_message)

    def pub_to(self):
        return ('wsn_data', 'fanout', '')

    def rx(self, body):
        """"
        {'source_addr': '\x00\x13\xa2\x00Aj\x07#',
         'data': "<=>\x06\x1eb'g\x05|\x10T\x13#\xc3{\xa8\n\xf3Y4b\xc8\x00\x00PA33\xabA\x00\x00\x00\x00",
         'id': 'rx',
         'options': '\xc2'}
        """
        source_addr = body['source_addr']

        # Skip source_addr, id and options
        data = body['data']
        frame = parse_frame.parse_frame(data)
        if frame is None:
            raise ValueError("Error parsing %s" % base64.b64encode(data))

        frame = frame[0]
        if not frame['name'] and frame['type'] != EVENT_FRAME:
            frame['name'] = self.db_get(source_addr, 'name', '')
        frame['received'] = body['received']
        frame['source_addr_long'] = source_addr
        self.publish(frame)
        self.db_update(source_addr, serial=frame['serial'], name=frame['name'])

        # Sending frames section
        bauds = int(self.config.get('bauds', 9600))
        address = struct.pack(">Q", source_addr)
        tst = int(time.time())

        # RSSI
        name = 'rssi_tst'
        threshold = ((1 * 60) - 5) * 60 # 55 minutes
        #threshold = 30 # 30s for testing
        #print('[rssi]', tst, threshold, self.db_get(source_addr, name, 0))
        if (tst - threshold) > self.db_get(source_addr, name, 0):
            with Serial('/dev/serial0', bauds) as serial:
                xbee = DigiMesh(serial)
                control.remote_at(xbee, address, command='DB')
            self.info('Asked for rssi')
            self.db_update(source_addr, **{name: tst})

        # Sync time
        name = 'cmd_time'
        threshold = ((6 * 60) - 5) * 60 # 6hours - 5minutes
        #threshold = 30 # 30s for testing
        #print('[time]', tst, threshold, self.db_get(source_addr, name, 0))
        if (tst - threshold) > self.db_get(source_addr, name, 0):
            data = 'time %d' % tst
            with Serial('/dev/serial0', bauds) as serial:
                xbee = DigiMesh(serial)
                # TODO autoincrement frame_id like we do with remote-at
                xbee.tx(dest_addr=address, data=data, frame_id='\x01')
            self.info('Sent "time" command')
            self.db_update(source_addr, **{name: tst})

    def remote_at_response(self, body):
        """
        {'command': b'DB',
         'body_id': b'\x06',
         'id': 'remote_at_response',
         'parameter': b'6',
         'source_addr': b'\x00\x13\xa2\x00A\x05\xd8\xcf',
         'status': b'\x00'}
        """
        if body['status'] != b'\x00':
            self.warning('REMOTE_AT Response failed %s', body)
            return

        if body['command'] != b'DB':
            self.warning('UNEXPECTED command %s', body['command'])
            return

        source_addr = body['source_addr']
        received = body['received']
        self.publish({
            'source_addr_long': source_addr,
            'name': self.db_get(source_addr, 'name', ''),
            'received': received,
            'serial': self.db_get(source_addr, 'serial'),
            'rssi': - struct.unpack('B', body['parameter'])[0],
        })

        # Update db
        self.db_update(source_addr, rssi_tst=received)

    def tx_status(self, body):
        self.warning('tx_status not implemented') # TODO

    def handle_message(self, body):
        # Decode
        for k in body.keys():
            if k not in ('id', 'received'):
                body[k] = base64.b64decode(body[k])

        # Decode: source_addr
        source_addr = body.get('source_addr')
        if source_addr is None:
            # Support source_addr_long so we're able to parse old raw frames
            source_addr = body.get('source_addr_long')

        if source_addr is not None:
            assert len(source_addr) == 8
            body['source_addr'] = struct.unpack(">Q", source_addr)[0]

        # Handle
        frame_type = body['id']
        handler = {
            'rx': self.rx,
            'remote_at_response': self.remote_at_response,
            'tx_status': self.tx_status,
        }.get(frame_type)

        if handler is None:
            self.warning('UNEXPECTED ID %s', frame_type)
            return

        handler(body)


if __name__ == '__main__':
    with Consumer() as consumer:
        consumer.start()
