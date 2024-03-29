# Standard Library
import base64
#import struct

# Project
import mq
import riot
import waspmote


EVENT_FRAME = 2 # Used to signal boot


class Consumer(mq.MQ):

    name = 'wsn_raw_cook'
    db_name = 'var/raw_cook.json'

    def sub_to(self):
        return ('wsn_raw', 'fanout', self.name, self.handle_message)

    def pub_to(self):
        return ('wsn_data', 'fanout', '')

    def rx(self, body):
        """"
        {'source_addr': '\x00\x13\xa2\x00Aj\x07#',
         'data': "<=>\x06\x1eb'g\x05|\x10T\x13#\xc3{\xa8\n\xf3Y4b\xc8\x00\x00PA33\xabA\x00\x00\x00\x00",
         'id': 'rx',
         'options': '\xc2'}
        """
        source_addr = body['source_addr']
        cipher_key = self.config.get('key')
        if cipher_key is not None:
            cipher_key = cipher_key.encode()

        # Skip source_addr, id and options
        data = body['data']

        # RIOT frames (cbor)
        fmt = self.config.get('format', 'waspmote')
        self.info('rx %s %s', fmt, data)
        if fmt == 'riot':
            try:
                frame = riot.parse_frame(data)
            except ValueError:
                self.error('Failed to load CBOR data')
            else:
                self.info('CBOR %s', frame)
                frame.update({
                    'received': body['received'],
                    'source_addr': source_addr,
                })
                self.publish(frame)

            return

        # Waspmote frames
        while data:
            try:
                frame, data = waspmote.parse_frame(data, cipher_key=cipher_key)
            except waspmote.FrameNotFound:
                break
            except waspmote.ParseError:
                # FIXME A package may contain several frames, if at least 1
                # frame has been processed, drop this event from the queue and
                # publish a new event with the remaining part.
                print(body)
                raise

            if not frame['name'] and frame['type'] != EVENT_FRAME:
                frame['name'] = self.get_state(source_addr, 'name', '')
            frame['received'] = body['received']
            frame['source_addr'] = source_addr
            self.publish(frame)
            self.set_state(source_addr, serial=frame['serial'], name=frame['name'])

#   def remote_at_response(self, body):
#       """
#       {'command': b'DB',
#        'body_id': b'\x06',
#        'id': 'remote_at_response',
#        'parameter': b'6',
#        'source_addr': b'\x00\x13\xa2\x00A\x05\xd8\xcf',
#        'status': b'\x00'}
#       """
#       if body['status'] != b'\x00':
#           self.warning('REMOTE_AT Response failed %s', body)
#           return

#       if body['command'] != b'DB':
#           self.warning('UNEXPECTED command %s', body['command'])
#           return

#       source_addr = body['source_addr']
#       received = body['received']
#       self.publish({
#           'source_addr': source_addr,
#           'name': self.get_state(source_addr, 'name', ''),
#           'received': received,
#           'serial': self.get_state(source_addr, 'serial'),
#           'rssi': - struct.unpack('B', body['parameter'])[0],
#       })

#       # Update db
#       self.set_state(source_addr, rssi_tst=received)

    def handle_message(self, body):
        # Decode
        for k in body.keys():
            if k not in ('id', 'received', 'source_addr'):
                body[k] = base64.b64decode(body[k])

        # Handle
        frame_type = body['id']
        handler = {
            'rx': self.rx,
#           'remote_at_response': self.remote_at_response,
        }.get(frame_type)

        if handler is None:
            self.warning('UNEXPECTED ID %s', frame_type)
            return

        handler(body)


if __name__ == '__main__':
    with Consumer() as consumer:
        consumer.start()
