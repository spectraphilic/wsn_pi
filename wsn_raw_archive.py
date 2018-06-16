# Standard Library
import base64
from datetime import date
import json
import os
import struct

from mq import MQ


class Consumer(MQ):

    name = 'wsn_raw_archive'

    def sub_to(self):
        return ('wsn_raw', 'fanout', self.name, self.handle_message)

    def get_dirname(self, body):
        frame_type = body['id']

        source_addr = body.get('source_addr')
        if source_addr is not None:
            source_addr = base64.b64decode(source_addr)
            assert len(source_addr) == 8
            source_addr = struct.unpack(">Q", source_addr)[0]
            return '%016X' % source_addr

        return frame_type

    def handle_message(self, body):
        # Create parent directory
        dirname = self.get_dirname(body)
        dirpath = os.path.join(datadir, dirname)
        os.makedirs(dirpath, exist_ok=True)

        # Append
        filename = date.fromtimestamp(body['received']).strftime('%Y%m%d')
        filepath = os.path.join(dirpath, filename)
        with open(filepath, 'a+') as f:
            body = json.dumps(body)
            f.write(body + '\n')


if __name__ == '__main__':
    datadir = os.path.join(os.getcwd(), 'data', 'raw')
    with Consumer() as consumer:
        consumer.start()
