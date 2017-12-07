# Standard Library
import base64
import struct

from mq import MQ
from parse_frame import parse_frame

class Consumer(MQ):

    name = 'wsn_cook'

    def sub_to(self):
        return ('wsn_raw', 'fanout', 'wsn_raw_cook', self.handle_message)

    def pub_to(self):
        return ('wsn_data', 'fanout', '')

    def handle_message(self, body):
        # Skip source_addr, id and options
        received = body['received']
        source_addr = base64.b64decode(body['source_addr_long'])
        source_addr = struct.unpack(">Q", source_addr)[0]
        rf_data = base64.b64decode(body['rf_data'])

        # Frame
        frame = parse_frame(rf_data)[0]
        frame['received'] = received
        frame['source_addr_long'] = source_addr

        self.publish(frame)


if __name__ == '__main__':
    with Consumer() as consumer:
        consumer.start()
