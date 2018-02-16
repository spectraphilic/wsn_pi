# Standard Library
from configparser import RawConfigParser as ConfigParser
import json
import logging
import signal
import sys

import pika


class MQ(object):
    """
    This class is to be used as a base class. Its main purpose is to provide
    access to the message broker, either as publisher or consumer.
    Additionnaly, it wraps config and logging.

    It is meant to be used as a context manager:

        class Publisher(MQ):
            name = 'xxx'

        with Publisher() as publisher:
            ...

    Only direct and fanout exchanges are supported.
    """

    name = ''
    host = 'localhost'
    sub_to = None
    pub_to = None
    bg_task = None # Background task

    def __init__(self):
        self.connection = None
        self.channel = None
        self.logger = logging.getLogger(self.name)
        self.started = False
        # Read configuration
        config = ConfigParser()
        config.read('config.ini')
        self.config = {}
        for section in ['global', self.name]:
            try:
                self.config.update(dict(config[section]))
            except KeyError:
                pass

        # Used to know when the setup process is done
        self.todo = set()

    def start(self):
        signal.signal(signal.SIGTERM, self.stop)
        self.info('Start. To exit press CTRL+C')
        self.started = True
        try:
            self.connection.ioloop.start()
        except KeyboardInterrupt:
            pass

    def stop(self, signum=None, frame=None):
        if self.channel is not None:
            self.channel.close()
            self.channel = None

        if self.connection is not None:
            self.connection.close()
            if self.started:
                self.connection.ioloop.start() # Graceful stop
                self.started = False

            self.connection = None

    def connect(self):
        parameters = pika.ConnectionParameters(host=self.host)
        self.connection = pika.SelectConnection(
            parameters,
            self.on_connect_open,
            self.on_connect_error,
            self.on_connect_close,
        )
        # Update todo
        self.todo.add('open_connection')

    def on_connect_open(self, connection):
        self.info('Connection open')
        connection.channel(self.on_channel_open)
        # Update todo
        self.todo.add('open_channel')
        self.todo.remove('open_connection')

    def on_connect_error(self, connection, exc):
        self.exception('Connection error')
        self.connection = None
        sys.exit(1)

    def on_connect_close(self, connection, reply_code, reply_text):
        self.info('Connection closed')

    def on_channel_open(self, channel):
        self.info('Channel open')
        self.channel = channel

        # Subscription
        if self.sub_to:
            exchange, exchange_type, queue, consumer = self.sub_to()
            cb = self.on_exchange_declare(exchange, queue, consumer)
            channel.exchange_declare(cb, exchange, exchange_type, durable=True)
            self.todo.add('declare_exchange_%s' % exchange)

        # Publication
        if self.pub_to:
            exchange, exchange_type, queue = self.pub_to()
            cb = self.on_exchange_declare(exchange, queue)
            channel.exchange_declare(cb, exchange, exchange_type, durable=True)
            self.todo.add('declare_exchange_%s' % exchange)

        # Update todo
        self.todo.remove('open_channel')

    def on_exchange_declare(self, exchange, queue, consumer=None):
        def callback(frame):
            self.info('Exchange declared name=%s', exchange)
            if queue or consumer:
                cb = self.on_queue_declare(exchange, queue, consumer)
                self.channel.queue_declare(cb, queue, durable=True)
                self.todo.add('declare_queue_%s' % queue)

            # Update todo
            self.todo.remove('declare_exchange_%s' % exchange)
            if not self.todo:
                self.done()

        return callback

    def on_queue_declare(self, exchange, queue, consumer):
        def callback(frame):
            self.info('Queue declared name=%s', queue)
            cb = self.on_queue_bind(exchange, queue, consumer)
            self.channel.queue_bind(cb, queue, exchange)
            # Update todo
            self.todo.add('bind_queue_%s' % queue)
            self.todo.remove('declare_queue_%s' % queue)

        return callback

    def on_queue_bind(self, exchange, queue, consumer):
        def callback(frame):
            self.info('Bound exchange=%s queue=%s', exchange, queue)
            if consumer:
                cb = self.on_message(consumer)
                self.channel.basic_consume(cb, queue=queue)

            # Update todo
            self.todo.remove('bind_queue_%s' % queue)
            if not self.todo:
                self.done()

        return callback

    def on_message(self, consumer):
        def callback(channel, method, header, body):
            try:
                body = body.decode()
                body = json.loads(body)
                consumer(body)
            except Exception:
                self.exception('Message handling failed')
                #channel.basic_reject(delivery_tag=method.delivery_tag)
            else:
                channel.basic_ack(delivery_tag=method.delivery_tag)
                self.debug('Message received and handled')

        return callback

    def done(self):
        self.info('Setup done.')
        # Background task
        if self.bg_task:
            self.connection.add_timeout(1, self.bg_task_wrapper)

    def bg_task_wrapper(self):
        self.bg_task()
        self.connection.add_timeout(1, self.bg_task_wrapper)

    #
    # Publisher
    #
    def publish(self, body):
        exchange, exchange_type, queue = self.pub_to()
        body = json.dumps(body)
        properties = pika.BasicProperties(
            delivery_mode=2, # persistent message
            content_type='application/json',
        )
        self.channel.basic_publish(
            exchange=exchange,
            routing_key=queue,
            properties=properties,
            body=body,
        )
        self.debug('Message published')

    #
    # Logging helpers
    #
    def init_logging(self):
        # Logging
        log_format = '%(asctime)s - %(name)s - %(threadName)s - %(levelname)s - %(message)s'
        log_level = self.config.get('log_level', 'info').upper()
        log_level = logging.getLevelName(log_level)
        logging.basicConfig(format=log_format, level=log_level, stream=sys.stdout)

    def debug(self, *args):
        self.logger.debug(*args)

    def info(self, *args):
        self.logger.info(*args)

    def warning(self, *args):
        self.logger.warning(*args)

    def error(self, *args):
        self.logger.error(*args)

    def critical(self, *args):
        self.logger.critical(*args)

    def exception(self, *args):
        self.logger.exception(*args)

    #
    # Context manager
    #
    def __enter__(self):
        self.init_logging()
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        logging.shutdown()
