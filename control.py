"""
Links:

https://groups.google.com/forum/#!topic/python-xbee/hC9EiZ9L1qU
https://stackoverflow.com/questions/14136053/what-are-the-frame-id-and-frame-fields-in-ser-send-from-python-xbee
http://docs.digi.com/pages/viewpage.action?pageId=2626044
https://cdn.sparkfun.com/learn/materials/29/22AT%20Commands.pdf
"""

# Standard Library
import argparse
from cmd import Cmd
from datetime import datetime
import signal
import struct
import time

from serial import Serial
from xbee import DigiMesh

# Constants
BAUDS = 9600
#BAUDS = 115200

# Xbee addresses
BROADCAST = b'\x00\x00\x00\x00\x00\x00\xff\xff'
CS_PI  = b'\x00\x13\xa2\x00\x41\x25\x39\xd3'
CS_V12 = b'\x00\x13\xa2\x00A%9m'
CS_V15 = b'\x00\x13\xa2\x00A\x05\xd8\xcf'
CS = [CS_V12, CS_V15]

FINSE = [
    5526146532103365,
    5526146532103350,
    5526146534160844,
]
FINSE = [struct.pack(">Q", x) for x in FINSE]

ADDRESSES = {
    'broadcast': BROADCAST,
    'v12': CS_V12,
    'v15': CS_V15,
}


def timeout(signum, frame):
    print('Timeout')
    raise TimeoutError


def test_simple():
    xbee.at(command="DB", frame_id="\x01") # Pi
    xbee.remote_at(command="DB", frame_id="\x01", dest_addr_long=CS_V12)
    xbee.remote_at(command="DB", frame_id="\x01", dest_addr_long=CS_V15)

    # Broadcast
    xbee.remote_at(command="DB", frame_id="\x01")
    xbee.remote_at(command="DB", frame_id="\x01", dest_addr_long=BROADCAST)


def remote_at(xbee, address, command, frame_ids={}):
    # frame_id is required
    frame_id = frame_ids.setdefault(address, 1)
    frame_ids[address] = 1 if (frame_id == 255) else (frame_id + 1) # Next
    frame_id = bytearray([frame_id])

    # Send AT command
    xbee.remote_at(dest_addr_long=address, command=command, frame_id=frame_id)
    return frame_id


def tx(xbee, address, data, frame_ids={}):
    # frame_id is required
    frame_id = frame_ids.setdefault(address, 1)
    frame_ids[address] = 1 if (frame_id == 255) else (frame_id + 1) # Next
    frame_id = bytearray([frame_id])

    # Send AT command
    xbee.tx(dest_addr=address, data=data, frame_id=frame_id)
    return frame_id


def remote_at_wait(xbee, address, command='DB', timeout=5):
    frame_id = remote_at(xbee, address, command)
    signal.alarm(timeout)
    try:
        while True:
            frame = xbee.wait_read_frame()
            if frame.get('frame_id') == frame_id:
                if address == BROADCAST:
                    print(frame)
                    return frame
                if frame['source_addr'] == address:
                    print(frame)
                    return frame
    except TimeoutError:
        pass

    return None


def retry(address, command='DB'):
    seconds = (60 - datetime.now().second) + 3
    time.sleep(seconds)
    for i in range(5):
        print('Try %s', datetime.now())
        frame = remote_at_wait(address, command)
        if frame['status'] == b'\x00':
            break

    return frame


def command(f):
    def wrapper(self, arg):
        args = arg.split()
        return f(self, *args)
    
    wrapper.__doc__ = f.__doc__
    return wrapper


class Control(Cmd):
    prompt = '() '
    address = None

    def preloop(self):
        self.serial = Serial('/dev/serial0', BAUDS)
        self.xbee = DigiMesh(self.serial)

    def set_address(self, address):
        if address not in ADDRESSES:
            address = ''

        self.address = address
        self.prompt = '(%s) ' % self.address

    @command
    def do_ls(self):
        """List motes."""
        for name in sorted(ADDRESSES):
            print(name)

    @command
    def do_set(self, address):
        """Change XBee address"""
        self.set_address(address)

    @command
    def do_at(self, command):
        """Send AT command"""
        remote_at_wait(self.xbee, ADDRESSES[self.address], command=command.upper())

    @command
    def do_tx(self, data):
        """Send AT command"""
        self.xbee.tx_long_addr(det_addr=ADDRESSES[self.address], data=data)

    @command
    def do_q(self):
        """Quit"""
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('address', default='')
    args = parser.parse_args()

    signal.signal(signal.SIGALRM, timeout)

    control = Control()
    control.set_address(args.address)
    control.cmdloop()

#   serial = Serial('/dev/serial0', BAUDS)
#   xbee = DigiMesh(serial)

#   data = 'time %d' % int(time.time())
#   data = b'hello'
#   xbee.tx_long_addr(dest_addr=CS_V15, data=data)

    #remote_at(xbee, CS_V15, command='DB')
    #print(xbee.wait_read_frame())
