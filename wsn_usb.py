# Standard Library
import time

# Requirements
from serial import Serial, SerialException

# Project
from mq import MQ
import waspmote


class Publisher(MQ):

    name = 'wsn_usb'
    db_name = 'var/usb.json'

    def pub_to(self):
        return ('wsn_data', 'fanout', '')

    def bg_task(self):
        #self.info('Background task: read from USB')
        if not serial.is_open:
            try:
                serial.open()
            except SerialException:
                return 30 # Try again 30s later
            else:
                self.info('Serial port open')

        try:
            timeout = 20 # Seconds waiting for a frame before giving up
            start = time.time()

            data = b''
            while time.time() < start + timeout:
                read = serial.read(1000)
                if not read:
                    time.sleep(0.01)
                    continue

                data += read
                try:
                    frame, data = waspmote.parse_frame(data)
                except waspmote.FrameNotFound:
                    continue
                except waspmote.ParseError:
                    # This should never happen
                    self.exception()
                except Exception:
                    # This will happen when the frame is not yet fully read from USB
                    continue
                else:
                    print(frame) # XXX
                    frame['received'] = int(time.time())

                    # TODO handle dups

                    self.publish(frame)
                    cmd = f'ack;time {int(time.time())}'
                    serial.write(cmd.encode())
                    start = time.time()
        except SerialException:
            serial.close()
            self.info('Serial port close')
            return 30 # Try again 30s later


if __name__ == '__main__':
    with Publisher() as publisher:
        config = publisher.config
        port = config.get('port', '/dev/serial0')
        bauds = int(config.get('bauds', 9600))
        with Serial() as serial:
            serial.port = port
            serial.baudrate = bauds
            serial.timeout = 0
            publisher.start()
