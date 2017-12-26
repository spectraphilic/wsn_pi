"""
Links:

https://groups.google.com/forum/#!topic/python-xbee/hC9EiZ9L1qU
https://stackoverflow.com/questions/14136053/what-are-the-frame-id-and-frame-fields-in-ser-send-from-python-xbee
http://docs.digi.com/pages/viewpage.action?pageId=2626044
https://cdn.sparkfun.com/learn/materials/29/22AT%20Commands.pdf
"""

# Standard Library
from datetime import datetime
import struct
import time

from serial import Serial
from xbee import XBee

# Xbee addresses
BROADCAST = b'\x00\x00\x00\x00\x00\x00\xff\xff'
CS_PI  = b'\x00\x13\xa2\x00\x41\x25\x39\xd3'
CS_V12 = b'\x00\x13\xa2\x00A%9m'
CS_V15 = b'\x00\x13\xa2\x00A\x05\xd8\xcf'
CS = [CS_V12, CS_V15]

FINSE = [
    5526146532103365,
    5526146532103350,
    5526146532103365,
    5526146534160844,
]
FINSE = [struct.pack(">Q", x) for x in FINSE]


def test_simple():
    xbee.at(command="DB", frame_id="\x01") # Pi
    xbee.remote_at(command="DB", frame_id="\x01", dest_addr_long=CS_V12)
    xbee.remote_at(command="DB", frame_id="\x01", dest_addr_long=CS_V15)

    # Broadcast
    xbee.remote_at(command="DB", frame_id="\x01")
    xbee.remote_at(command="DB", frame_id="\x01", dest_addr_long=BROADCAST)


def send(address, command='DB', frame_ids={}):
    frame_id = frame_ids.setdefault(address, 1)
    frame_ids[address] = 1 if (frame_id == 255) else (frame_id + 1) # Next

    frame_id = chr(frame_id).encode()
    xbee.remote_at(command=command, frame_id=frame_id, dest_addr_long=address)
    return frame_id


def send_recv(address, command='DB'):
    frame_id = send(address, command)
    while True:
        frame = xbee.wait_read_frame()
        if frame.get('frame_id') == frame_id:
            if address == BROADCAST:
                break
            if frame['source_addr_long'] == address:
                break

    return frame


def delay(address, command='DB'):
    seconds = (60 - datetime.now().second) + 4
    time.sleep(seconds)
    return send(address, command)


def retry(address, command='DB'):
    seconds = (60 - datetime.now().second) + 3
    time.sleep(seconds)
    for i in range(5):
        print('Try %s', datetime.now())
        frame = send_recv(address, command)
        if frame['status'] == b'\x00':
            break

    return frame


def cron():
    second = 4
    now = datetime.now()
    if now.second < second:
        time.sleep(second - now.second)

    addresses = FINSE
    #addresses = CS
    for address in addresses:
        send(address, 'DB')


if __name__ == '__main__':
    serial = Serial('/dev/serial0', 115200)
    xbee = XBee(serial)

    cron()
    #send(CS_V15)
    #print(xbee.wait_read_frame())
