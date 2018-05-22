# Standard Library
import base64
import contextlib
from queue import Queue, Empty
import struct
import time

from serial import Serial
from xbee import DigiMesh

from mq import MQ


class Publisher(MQ):

    name = 'wsn_xbee'
    db_name = 'var/xbee.json'

    def pub_to(self):
        return ('wsn_raw', 'fanout', '')

    def bg_task(self):
        while True:
            try:
                frame = queue.get_nowait()
            except Empty:
                return

            t0 = time.time()
            self.debug('FRAME %s', frame)

            # Skip duplicates
            if frame['id'] == 'rx':
                address = struct.unpack(">Q", frame['source_addr'])[0]
                data = base64.b64encode(frame['data']).decode()
                if data == self.db_get(address, 'data'):
                    self.info('Dup frame detected and skipped')
                    continue
                self.db_update(address, data=data)

            # Prepare data to publish
            data = {'received': int(t0)} # Timestamp
            for key, value in frame.items():
                if key != 'id':
                    value = base64.b64encode(value).decode() # Base 64
                if key != 'received':
                    data[key] = value

            # Publish
            self.publish(data)
            queue.task_done()

            # Send ACK to mote
            if frame['id'] == 'rx':
                address = frame['source_addr']
                xbee.tx(dest_addr=address, data='ack', frame_id='\x01')

            # Log
            self.info('Message sent in %f seconds', time.time() - t0)

    #
    # XBee callbaks, defined here to use the logging helpers
    #
    def xbee_cb(self, frame):
        t0 = time.time()
        queue.put(frame)
        self.debug('Frame pushed in %f seconds', time.time() - t0)

    def xbee_cb_error(self, exc):
        self.exception('Publication failed')


@contextlib.contextmanager
def xbee_manager(serial, callback, error_callback=None):
    try:
        # Starts XBee thread
        xbee = DigiMesh(serial, callback=callback, error_callback=error_callback)
        yield xbee
    finally:
        xbee.halt() # Stop XBee thread

if __name__ == '__main__':
    queue = Queue()
    with Publisher() as publisher:
        bauds = int(publisher.config.get('bauds', 9600))
        with Serial('/dev/serial0', bauds) as serial:
            with xbee_manager(serial, publisher.xbee_cb, publisher.xbee_cb_error) as xbee:
                publisher.start()
