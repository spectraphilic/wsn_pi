# Standard Library
import base64
#from datetime import datetime
import time

# Project
import control, utils
from mq import MQ


class Publisher(MQ):

    name = 'wsn_xbee'
    db_name = 'var/xbee.json'

    def pub_to(self):
        return ('wsn_raw', 'fanout', '')

    def xbee_cb(self, message):
        remote = message.remote_device
        t0 = time.time()

        # Ping
        data = message.data
        self.info('RCV %s', data)
        if data == b'ping':
            self.info('> ping')
            msg = "pong %s" % int(time.time())
            device.send_data_broadcast(msg)
            self.info("< %s", msg)
            return

        # Remote / Address (hex)
        address = utils.get_address(remote)
        address = address.address.hex().upper()

        # Skip duplicates
        data = base64.b64encode(data).decode()
        if data == self.get_state(address, 'data'):
            self.info('Dup frame detected and skipped')
            control.tx(device, remote, 'ack')
            return
        self.set_state(address, data=data)

        # Publish
        frame = {
            'id': 'rx', # XXX remote_at_response, tx_status
            'source_addr': address,
            'data': base64.b64encode(message.data).decode(),
            'received': int(message.timestamp),
        }
        self.publish(frame)

        # Send ACK to mote
        control.tx(device, remote, 'ack')

        # Sync time (once every 6h)
        name = 'cmd_time'
        threshold = ((6 * 60) - 5) * 60 # 6hours - 5minutes
        #threshold = 30 # 30s for testing
        current = self.get_state(address, name, 0)
        #print('[time]', datetime.fromtimestamp(t0), datetime.fromtimestamp(current), threshold)
        if (t0 - threshold) > current:
            control.tx(device, remote, 'time %d' % int(t0))
            self.info('Sent "time" command')
            self.set_state(address, **{name: t0})


if __name__ == '__main__':
    with Publisher() as publisher:
        device = utils.get_device(publisher.config)
        try:
            device.open()
            device.add_data_received_callback(publisher.xbee_cb)
            publisher.start()
        finally:
            if device.is_open():
                device.close()
