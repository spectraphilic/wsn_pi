# Standard library
import base64
import collections
import contextlib
import threading
import time

# Requirements
import cbor2
try:
    from rak811.rak811_v3 import Rak811, Rak811ResponseError
except RuntimeError:
    pass

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


class Package(collections.namedtuple('Package', ['dst', 'src', 'packnum', 'length', 'payload', 'retry'])):

    def to_bytes(self):
        data = (
            self.dst.to_bytes(1, 'little')
            + self.src.to_bytes(1, 'little')
            + self.packnum.to_bytes(1, 'little')
            + self.length.to_bytes(1, 'little')
            + self.payload
            + self.retry.to_bytes(1, 'little')
        )
        return data

def parse_waspmote(data):
    dst = data[0]
    src = data[1]
    packnum = data[2]
    length = data[3]
    payload = data[4:-1]
    retry = data[-1]
    assert length == len(data)
    return Package(dst, src, packnum, length, payload, retry)


def parse_cbor2(data):
    array = cbor2.loads(data)
    assert type(array) is list and len(array) >= 2 and array[0] == 0
    src = array[1]
    assert type(src) is int and 2 <= src <= 255
    dst = array[3]
    return Package(dst, src, 0, data, 0)


def lora_recv(lora, publisher):
    parsers = {
        'waspmote': parse_waspmote,
        'riot': parse_cbor2,
    }
    fmt = publisher.config.get('format', 'waspmote')
    parse = parsers[publisher.config.get('format', 'waspmote')]
    address = int(publisher.config.get('address', 1))

    while lora.nb_downlinks > 0:
        message = lora.get_downlink()  # keys: data, len, port, rssi, snr
        received = int(time.time())
        publisher.info(f'Received message len={message["len"]} rssi={message["rssi"]} snr={message["snr"]}')
        data = message['data']
        data_str = base64.b64encode(data).decode()

        # Extract source address from data
        try:
            pkg = parse(data)
        except Exception:
            publisher.error(f'Failed to load {fmt} data from {data_str}')
            continue

        # Filter packets not send to me or to broadcast
        if pkg.dst != address and pkg.dst != 0:
            publisher.info(f'Skip package addressed to {pkg.dst}')
            continue

        if pkg.payload == b'ping':
            # Reply ACK
            ack = Package(pkg.src, address, pkg.packnum, 0, b'\x00', 0)
            ack = ack.to_bytes()
            lora_send(lora, ack)
            lora.set_config('lorap2p:transfer_mode:1')
            continue

        yield {
            'id': 'rx',
            'source_addr': str(pkg.src),
            'data': data_str,
            'received': received,
        }


def lora_send(lora, data):
    lora.set_config('lorap2p:transfer_mode:2')
    lora.send_p2p(data)

def lora_send_cbor2(lora, message):
    data = cbor2.dumps(message)
    lora_send(data)


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
            # FIXME This doesn't work with the waspmote
            target = int(msg['source_addr'])
            lora_send_cbor2(lora, [
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
