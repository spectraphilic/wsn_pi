import requests

from mq import MQ
import waspmote


class Consumer(MQ):

    name = 'wsn_data_django'

    def __init__(self):
        super().__init__()
        self.url = self.config['url']
        self.headers = {'Authorization': 'Token %s' % self.config['token']}

    def sub_to(self):
        return ('wsn_data', 'fanout', self.name, self.handle_message)

    def handle_message(self, data):
        json = waspmote.data_to_json(data)
        response = requests.post(self.url, json=json, headers=self.headers)
        status = response.status_code
        assert status == 201, '{} {}'.format(status, response.json())


if __name__ == '__main__':
    with Consumer() as consumer:
        consumer.start()
