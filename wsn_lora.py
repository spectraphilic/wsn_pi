# Standard library
from contextlib import contextmanager

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

@contextmanager
def open_lora():
    print('Initializing RAK811 module...')
    lora = Rak811()
    try:
        lora = Rak811()
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
        print('GOT MESSAGE...')
        message = lora.get_downlink()
        data = message['data']
        data = int.from_bytes(data, byteorder='big')
        print(f'Received message: {data}')
        print(f'RSSI: {message["rssi"]}, SNR: {message["snr"]}')
        yield data


def lora_send(lora, message):
    lora.set_config('lorap2p:transfer_mode:2')
    lora.send_p2p(message)


def loop(lora, publisher):
    while True:
        # Receive mode
        lora.set_config('lorap2p:transfer_mode:1')
        wait_time = 60
        for data in lora.receive_p2p(wait_time):
            publisher.publish({
                'data': data,
            })


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
            #device.add_data_received_callback(publisher.lora_cb)
            #publisher.start()

            loop()
