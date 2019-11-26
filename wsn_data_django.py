import requests
from requests import exceptions

from mq import MQ, Pause
import waspmote


class Consumer(MQ):

    name = 'wsn_data_django'
    prefetch_count = 20

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
        try:
            response = self.session.post(
                self.url,
                json=json,
                headers=self.headers,
                timeout=timeout
            )
        except (exceptions.ConnectionError, exceptions.ReadTimeout) as exc:
            self.warning(str(exc))
            raise Pause(5*60)

        # Check response
        status = response.status_code
        text = response.text
        assert status == 201, 'Unexpected status=%s text=%s' % (status, text)


if __name__ == '__main__':
    with Consumer() as consumer:
        consumer.start()
