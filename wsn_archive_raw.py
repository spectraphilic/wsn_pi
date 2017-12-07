# Standard Library
import base64
from datetime import date
import json
import os
import struct

from mq import MQ

class Consumer(MQ):

    name = 'wsn_archive_raw'

    def sub_to(self):
        return ('wsn_raw', 'fanout', 'wsn_archive_raw', self.handle_message)

    def handle_message(self, body):
        received = body['received']
        source_addr = base64.b64decode(body['source_addr_long'])
        source_addr = struct.unpack(">Q", source_addr)

        # Create parent directory
        dirpath = os.path.join(datadir, '%016X' % source_addr)
        os.makedirs(dirpath, exist_ok=True)

        # Append
        received = date.fromtimestamp(received).strftime('%Y%m%d')
        filepath = os.path.join(dirpath, received)
        with open(filepath, 'a+') as f:
            body = json.dumps(body)
            f.write(body + '\n')


if __name__ == '__main__':
    datadir = os.path.join(os.getcwd(), 'data', 'raw')
    with Consumer() as consumer:
        consumer.start()
