# Standard library
import base64
import contextlib
import threading
import time

# Requirements
from rak811.rak811_v3 import Rak811

# Project
from mq import MQ


# Use RIOT defaults for frequency and sf/bw/cr
freq = 868.300
sf = 7  # spreading factor
bw = 0  # bandwith (0 = 125KHz)
cr = 1  # coding rate (1 = 4/5)
pre = 8
pwr = 16

@contextlib.contextmanager
def open_lora():
    print('Initializing RAK811 module...')
    lora = Rak811()
    try:
        response = lora.set_config('lora:work_mode:1')
        for r in response:
            print(r)

        config = f'lorap2p:{int(freq*1000*1000)}:{sf}:{bw}:{cr}:{pre}:{pwr}'
        lora.set_config(config)

        yield lora
    finally:
        lora.close()


def lora_recv(lora):
    while lora.nb_downlinks > 0:
        message = lora.get_downlink()  # keys: data, len, port, rssi, snr
        received = int(time.time())
        print(f'Received message len={message["len"]} rssi={message["rssi"]} snr={message["snr"]}')
        data = message['data']
        data = base64.b64encode(data).decode()
        yield {
            'id': 'rx',
            'source_addr': '0', # FIXME
            'data': data,
            'received': received,
        }


def lora_send(lora, message):
    lora.set_config('lorap2p:transfer_mode:2')
    lora.send_p2p(message)


def loop(lora, publisher):
    while True:
        # Receive mode
        lora.set_config('lorap2p:transfer_mode:1')
        wait_time = 60
        lora.receive_p2p(wait_time)
        for msg in lora_recv(lora):
            publisher.publish(msg)


class Publisher(MQ):

    name = 'wsn_lora'
    db_name = 'var/lora.json'

    def pub_to(self):
        return ('wsn_raw', 'fanout', '')

    def lora_cb(self, message):
        pass


if __name__ == '__main__':
    with Publisher() as publisher:
        with open_lora() as lora:
            thread = threading.Thread(target=loop, args=(lora, publisher))
            thread.start()
            publisher.start()
