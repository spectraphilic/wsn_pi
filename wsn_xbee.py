# Standard Library
import base64
import contextlib
from queue import Queue, Empty
import signal
import time

from serial import Serial
from xbee import XBee

from mq import MQ

class Publisher(MQ):

    name = 'wsn_xbee'

    def pub_to(self):
        return ('wsn_raw', 'fanout', '')

    def bg_task(self):
        # {'source_addr_long': '\x00\x13\xa2\x00Aj\x07#', 'rf_data': "<=>\x06\x1eb'g\x05|\x10T\x13#\xc3{\xa8\n\xf3Y4b\xc8\x00\x00PA33\xabA\x00\x00\x00\x00", 'source_addr': '\xff\xfe', 'id': 'rx', 'options': '\xc2'}
        while True:
            try:
                frame = queue.get_nowait()
            except Empty:
                return

            t0 = time.time()
            self.debug('FRAME %s', frame)
            if frame['id'] != 'rx':
                self.warning('UNEXPECTED ID %s', frame['id'])
                continue

            for k in frame.keys():
                if k != 'id':
                    frame[k] = base64.b64encode(frame[k]).decode()

            # Add timestamp
            frame['received'] = int(t0)

            # Publish
            self.publish(frame)
            queue.task_done()
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


def sigterm(signum, frame):
    publisher.stop()

@contextlib.contextmanager
def xbee_manager(serial, callback, error_callback=None):
    try:
        # Starts XBee thread
        xbee = XBee(serial, callback=callback, error_callback=error_callback)
        yield xbee
    finally:
        xbee.halt() # Stop XBee thread

if __name__ == '__main__':
    queue = Queue()
    with Publisher() as publisher:
        bauds = int(publisher.config.get('bauds', 9600))
        with Serial('/dev/serial0', bauds) as serial:
            with xbee_manager(serial, publisher.xbee_cb, publisher.xbee_cb_error):
                signal.signal(signal.SIGTERM, sigterm) # Signal sent by Supervisor
                publisher.start()
