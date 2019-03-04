import requests

from mq import MQ
import waspmote


class Consumer(MQ):

    name = 'wsn_data_django'

    def __init__(self):
        super().__init__()
        self.url = self.config['url']
        self.headers = {'Authorization': 'Token %s' % self.config['token']}
        self.session = requests.Session()

    def sub_to(self):
        return ('wsn_data', 'fanout', self.name, self.handle_message)

    def handle_message(self, data):
        # RabbitMQ timeouts after 60s, so we must finish in less than 60s or
        # the connection to RabbitMQ will be broken.
        json = waspmote.data_to_json(data)
        # 5s to connect. And 30s between reception of bytes; XXX this does not
        # guarantees that we'll finish below 60s, so there's room for
        # improvement.
        timeout = (5, 30)
        response = self.session.post(self.url, json=json, headers=self.headers, timeout=timeout)
        status = response.status_code
        assert status == 201, '{} {}'.format(status, response.json())


if __name__ == '__main__':
    with Consumer() as consumer:
        consumer.start()
