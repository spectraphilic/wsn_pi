# Standard Library
from datetime import date
import json
import os

from mq import MQ


class Consumer(MQ):

    name = 'wsn_data_archive'

    def sub_to(self):
        return ('wsn_data', 'fanout', self.name, self.handle_message)

    def get_dirname(self, body):
        source_addr = body.get('source_addr_long')
        if source_addr is None:
            return 'null'

        return '%016X' % source_addr

    def handle_message(self, body):
        # Create parent directory
        dirname = self.get_dirname(body)
        dirpath = os.path.join(datadir, dirname)
        os.makedirs(dirpath, exist_ok=True)

        # Append
        received = body['received']
        received = date.fromtimestamp(received).strftime('%Y%m%d')
        filepath = os.path.join(dirpath, received)
        with open(filepath, 'a+') as f:
            body = json.dumps(body)
            f.write(body + '\n')


if __name__ == '__main__':
    datadir = os.path.join(os.getcwd(), 'data', 'cooked')
    with Consumer() as consumer:
        consumer.start()
