import base64
import collections
import threading
import time

# Requirements
import cbor2
try:
    from rak811.rak811_v3 import Rak811
except RuntimeError:
    pass

# Project
from mq import MQ


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


class LoRa:

    def __init__(self, publisher):
        self.__publisher = publisher
        self.__lora = None
        self.__address = int(publisher.config.get('address', 1))
        self.__format = publisher.config.get('format', 'waspmote')
        self.__packnum = 0

    def __enter__(self):
        print('Initializing RAK811 module...')

        # Use RIOT defaults for frequency and sf/bw/cr
        config = self.__publisher.config
        freq = int(config.get('khz', 868300)) * 1000
        sf = config.get('sf', 7) # spreading factor
        bw = config.get('bw', 0) # bandwith (0 = 125KHz)
        cr = 1                   # coding rate (1 = 4/5)
        pre = 8
        pwr = 16

        self.__lora = Rak811()
        response = self.__lora.set_config('lora:work_mode:1')
        for r in response:
            print(r)

        lora_config = f'lorap2p:{freq}:{sf}:{bw}:{cr}:{pre}:{pwr}'
        self.__lora.set_config(lora_config)
        return self

    def __exit__(self, type, value, traceback):
        self.__lora.close()

    def __build_pkg(self, dst, payload, packnum=None, length=None):
        assert type(payload) is bytes
        assert len(payload) <= 250
        if packnum is None:
            packnum = self.__packnum
            self.__packnum = (packnum + 1) % 256
        if length is None:
            length = 5 + len(payload)

        retry = 0
        pkg = Package(dst, self.__address, packnum, length, payload, retry)
        return pkg.to_bytes()

    def __send(self, data):
        self.__lora.set_config('lorap2p:transfer_mode:2')
        self.__lora.send_p2p(data)

    @staticmethod
    def parse_waspmote(data):
        """
        The waspmote library (see "Waspmote LoRa Networking Guide") sends packets with the
        following structure:

        - dst (1 Byte)
        - src (1 Byte)
        - packnum (1 Byte)
        - length (1 Byte)
        - data (variable)
        - retry (1 Byte)
        """
        dst = data[0]
        src = data[1]
        packnum = data[2]
        length = data[3]
        payload = data[4:-1]
        retry = data[-1]
        #print(f'DEBUG {dst=} {src=} {packnum=} {length=}, {retry=}')
        assert length == len(data), f'Got {len(data)} bytes, expected {length}'
        return Package(dst, src, packnum, length, payload, retry)

    @staticmethod
    def parse_cbor2(data):
        array = cbor2.loads(data)
        assert type(array) is list and len(array) >= 2 and array[0] == 0
        src = array[1]
        assert type(src) is int and 2 <= src <= 255
        dst = array[3]
        return Package(dst, src, 0, data, 0)

    def send(self, dst, payload, packnum=None, length=None):
        assert type(payload) is bytes
        if self.__format == 'waspmote':
            data = self.__build_pkg(dst, payload, packnum=packnum, length=length)
        else:
            payload = [self.__address, dst, payload]
            data = cbor2.dumps(payload)

        assert type(data) is bytes
        assert len(data) <= 255
        self.__send(data)

    def send_cbor2(self, message):
        data = cbor2.dumps(message)
        self.__send(data)

    def recv(self):
        lora = self.__lora
        publisher = self.__publisher

        while lora.nb_downlinks > 0:
            message = lora.get_downlink()
            received = int(time.time())

            # Read from the serial device: at+recv=,<rssi>,<snr>,<len>[:<data>]
            length = message['len']
            rssi = message['rssi']
            snr = message['snr']
            data = message['data']
            publisher.info(f'Received message len={length} rssi={rssi} snr={snr}')
            if length != len(data):
                publisher.error(f'Data length is {len(data)}, should be {length}')
                continue

            # Extract source address from data
            data_str = base64.b64encode(data).decode()
            try:
                if self.__format == 'waspmote':
                    pkg = self.parse_waspmote(data)
                else:
                    pkg = self.parse_cbor2(data)
            except Exception:
                publisher.error(f'Failed to load {self.__format} data from {data_str}')
                continue

            # Filter packets not send to me or to broadcast
            if pkg.dst != self.__address and pkg.dst != 0:
                publisher.info(f'Skip package addressed to {pkg.dst}')
                continue

            if pkg.payload == b'ping':
                # Reply ACK
                self.send(pkg.src, b'\x00', packnum=pkg.packnum, length=0)
                lora.set_config('lorap2p:transfer_mode:1')
                continue

            yield {
                'id': 'rx',
                'source_addr': str(pkg.src),
                'data': data_str,
                'received': received,
            }


    def loop(self):
        lora = self.__lora
        publisher = self.__publisher

        wait_time = 60
        while True:
            try:
                lora.set_config('lorap2p:transfer_mode:1') # Receive mode
                lora.receive_p2p(wait_time)
                for msg in self.recv():
                    publisher.publish(msg)
                    dst = int(msg['source_addr'])
                    self.send(dst, b'ack')

            except Exception as exc:
                publisher.warning(str(exc))


class Publisher(MQ):

    name = 'wsn_lora'
    db_name = 'var/lora.json'

    def pub_to(self):
        return ('wsn_raw', 'fanout', '')

    def lora_cb(self, message):
        pass


if __name__ == '__main__':
    with Publisher() as publisher:
        with LoRa(publisher) as lora:
            thread = threading.Thread(target=lora.loop, args=())
            thread.start()
            publisher.start()
