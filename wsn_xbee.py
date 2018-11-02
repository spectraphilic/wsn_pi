# Standard Library
import base64
import contextlib
#from datetime import datetime
from queue import Queue, Empty
import struct
import time

from serial import Serial
from xbee import DigiMesh

import control
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

            # The tx_status frame means the frame was sent without error (it
            # doesn't mean it was received at the other end)
            frame_id = frame['id']
            if frame_id == 'tx_status':
                # TODO Match this frame with the outgoing frame. The tx_status
                # frame doesn't have the source_addr field, so this may be a
                # bit harder.
                self.debug('tx_status not implemented')
                continue

            # Log
            address = frame['source_addr'] # used in control.tx/remote_at
            address_int = struct.unpack(">Q", address)[0] # Key in db
            self.debug('FRAME {} from {}'.format(frame, address_int))

            # Skip duplicates
            if frame_id == 'rx':
                data = frame['data']
                if data == b'ping':
                    self.info('ping')
                    continue
                data = base64.b64encode(data).decode()
                if data == self.get_state(address_int, 'data'):
                    self.info('Dup frame detected and skipped')
                    control.tx(xbee, address, 'ack')
                    continue
                self.set_state(address_int, data=data)

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
            if frame_id == 'rx':
                control.tx(xbee, address, 'ack')

            # RSSI (once an hour)
            name = 'rssi_tst'
            threshold = 55 * 60 # 55 minutes
            #threshold = 30 # 30s for testing
            current = self.get_state(address_int, name, 0)
            #print('[rssi]', datetime.fromtimestamp(t0), datetime.fromtimestamp(current), threshold)
            if (t0 - threshold) > current:
                control.remote_at(xbee, address, command='DB')
                self.info('Asked for rssi')
                self.set_state(address_int, **{name: t0})

            # Sync time (once every 6h)
            name = 'cmd_time'
            threshold = ((6 * 60) - 5) * 60 # 6hours - 5minutes
            #threshold = 30 # 30s for testing
            current = self.get_state(address_int, name, 0)
            #print('[time]', datetime.fromtimestamp(t0), datetime.fromtimestamp(current), threshold)
            if (t0 - threshold) > self.get_state(address_int, name, 0):
                control.tx(xbee, address, 'time %d' % int(t0))
                self.info('Sent "time" command')
                self.set_state(address_int, **{name: t0})

            # Log
            self.info('Message published in %f seconds', time.time() - t0)

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
