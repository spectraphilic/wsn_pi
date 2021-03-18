# Standard Library
import time

# Requirements
from serial import Serial

# Project
from mq import MQ
import waspmote


class Publisher(MQ):

    name = 'wsn_usb'
    db_name = 'var/usb.json'

    def pub_to(self):
        return ('wsn_data', 'fanout', '')

    def bg_task(self):
        data = b''
        while True:
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
                # This will when the frame is not yet fully read from the USB
                continue
            else:
                print('<', frame)
                frame['received'] = int(time.time())

                # TODO handle dups

                self.publish(frame)
                cmd = f'ack;time {int(time.time())}'
                serial.write(cmd.encode())


if __name__ == '__main__':
    with Publisher() as publisher:
        config = publisher.config
        port = config.get('port', '/dev/serial0')
        bauds = int(config.get('bauds', 9600))
        with Serial(port, bauds, timeout=0) as serial:
            publisher.start()
