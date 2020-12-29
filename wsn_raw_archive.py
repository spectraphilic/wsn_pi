# Standard Library
from datetime import date
import json
import os

from mq import MQ


class Consumer(MQ):

    name = 'wsn_raw_archive'

    def sub_to(self):
        return ('wsn_raw', 'fanout', self.name, self.handle_message)

    def get_dirname(self, body):
        return body['source_addr']

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
