# Standard Library
import base64
import struct

from mq import MQ
from parse_frame import parse_frame

class Consumer(MQ):

    name = 'wsn_raw_cook'

    def sub_to(self):
        return ('wsn_raw', 'fanout', self.name, self.handle_message)

    def pub_to(self):
        return ('wsn_data', 'fanout', '')

    def handle_rx(self, body):
        """"
        {'source_addr_long': '\x00\x13\xa2\x00Aj\x07#',
         'rf_data': "<=>\x06\x1eb'g\x05|\x10T\x13#\xc3{\xa8\n\xf3Y4b\xc8\x00\x00PA33\xabA\x00\x00\x00\x00",
         'source_addr': '\xff\xfe',
         'id': 'rx',
         'options': '\xc2'}
        """
        # Skip source_addr, id and options
        frame = parse_frame(body['rf_data'])[0]
        frame['received'] = body['received']
        frame['source_addr_long'] = body['source_addr_long']
        self.publish(frame)

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

        self.publish({
            'received': body['received'],
            'source_addr_long': body['source_addr_long'],
            'rssi': - struct.unpack('B', body['parameter'])[0],
        })

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
    with Consumer() as consumer:
        consumer.start()
