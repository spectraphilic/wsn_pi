# Standard Library
from datetime import datetime, timezone

import requests

from mq import MQ


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


class Consumer(MQ):

    name = 'wsn_data_django'

    def __init__(self):
        super().__init__()
        self.url = self.config['url']
        self.headers = {'Authorization': 'Token %s' % self.config['token']}

    def sub_to(self):
        return ('wsn_data', 'fanout', self.name, self.handle_message)

    def handle_message(self, data):
        json = data_to_json(data)
        response = requests.post(self.url, json=json, headers=self.headers)
        status = response.status_code
        assert status == 201, '{} {}'.format(status, response.json())


if __name__ == '__main__':
    with Consumer() as consumer:
        consumer.start()
