import requests

from mq import MQ


class Consumer(MQ):

    name = 'wsn_2django'

    def __init__(self):
        super().__init__()
        self.url = self.config['url']
        self.headers = {'Authorization': 'Token %s' % self.config['token']}

    def sub_to(self):
        return ('wsn_data', 'fanout', 'wsn_2django', self.handle_message)

    def handle_message(self, body):
        requests.post(self.url, json=body, headers=self.headers)


if __name__ == '__main__':
    with Consumer() as consumer:
        consumer.start()
