# Standard Library
from datetime import date
import json
import os

from mq import MQ

class Consumer(MQ):

    name = 'wsn_data_archive'

    def sub_to(self):
        return ('wsn_data', 'fanout', self.name, self.handle_message)

    def handle_message(self, body):
        received = body['received']
        source_addr = body['source_addr_long']

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
    datadir = os.path.join(os.getcwd(), 'data', 'cooked')
    with Consumer() as consumer:
        consumer.start()