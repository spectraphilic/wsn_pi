"""
Sometimes there may be a bug, for instance in parse_frame. This script will
re-publish the raw frames stored in the given file, to the wsn_raw_cook
channel.

TODO Declare the exchanges as direct (or topic or headers), not fanouts, to
have more control. Because right now the messages will be sent to every queue
subscribed, doesn't matter the routing key used.
"""

import json
import sys

import pika


if __name__ == '__main__':
    exchange, queue = 'wsn_raw', 'wsn_raw_cook'

    parameters = pika.ConnectionParameters(host='localhost')
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    properties = pika.BasicProperties(
        delivery_mode=2, # persistent message
        content_type='application/json',
    )

    try:
        for filename in sys.argv[1:]:
            print(filename)
            lines = open(filename).readlines()
            for line in lines:
                data = json.loads(line)
                data = json.dumps(data)
                channel.basic_publish(exchange, queue, data, properties)
    finally:
        connection.close()
