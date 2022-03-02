# Standard library
import base64
import contextlib
import threading
import time

# Requirements
import cbor2
from rak811.rak811_v3 import Rak811, Rak811ResponseError

# Project
from mq import MQ


@contextlib.contextmanager
def open_lora(config):
    print('Initializing RAK811 module...')

    # Use RIOT defaults for frequency and sf/bw/cr
    freq = int(config.get('khz', 868300)) * 1000
    sf = config.get('sf', 7) # spreading factor
    bw = config.get('bw', 0) # bandwith (0 = 125KHz)
    cr = 1                   # coding rate (1 = 4/5)
    pre = 8
    pwr = 16

    lora = Rak811()
    try:
        response = lora.set_config('lora:work_mode:1')
        for r in response:
            print(r)

        lora_config = f'lorap2p:{freq}:{sf}:{bw}:{cr}:{pre}:{pwr}'
        lora.set_config(lora_config)

        yield lora
    finally:
        lora.close()


def lora_recv(lora, publisher):
    while lora.nb_downlinks > 0:
        message = lora.get_downlink()  # keys: data, len, port, rssi, snr
        received = int(time.time())
        print(f'Received message len={message["len"]} rssi={message["rssi"]} snr={message["snr"]}')
        data = message['data']
        data_str = base64.b64encode(data).decode()

        # Extract source address from data
        try:
            array = cbor2.loads(data)
            assert type(array) is list and len(array) >= 2 and array[0] == 0
            source_addr = array[1]
            assert type(source_addr) is int and 2 <= source_addr <= 255
            source_addr = str(source_addr)
        except Exception:
            publisher.error('Failed to load CBOR data or read source address from {data_str}')
            continue

        yield {
            'id': 'rx',
            'source_addr': source_addr,
            'data': data_str,
            'received': received,
        }


def lora_send(lora, message):
    lora.set_config('lorap2p:transfer_mode:2')
    message = cbor2.dumps(message)
    lora.send_p2p(message)


def loop(lora, publisher):
    while True:
        # Receive mode
        lora.set_config('lorap2p:transfer_mode:1')
        wait_time = 60
        try:
            lora.receive_p2p(wait_time)
        except Rak811ResponseError as exc:
            publisher.warning(str(exc))
            continue

        for msg in lora_recv(lora, publisher):
            publisher.publish(msg)
            # Send ack
            target = int(msg['source_addr'])
            lora_send(lora, [
                1,          # Source address (gateway)
                target,     # Target address
                'ack',      # Command
            ])


class Publisher(MQ):

    name = 'wsn_lora'
    db_name = 'var/lora.json'

    def pub_to(self):
        return ('wsn_raw', 'fanout', '')

    def lora_cb(self, message):
        pass


if __name__ == '__main__':
    with Publisher() as publisher:
        with open_lora(publisher.config) as lora:
            thread = threading.Thread(target=loop, args=(lora, publisher))
            thread.start()
            publisher.start()
