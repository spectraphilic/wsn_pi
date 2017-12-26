Install
=======

Install system wide requirements::

  $ sudo apt-get install python3-venv
  $ sudo apt-get install rabbitmq-server
  $ sudo apt-get install supervisor

Build::

  $ make install
  $ crontab crontab.txt

Create a symbolic link, as root, to the supervisor configuration::

  $ sudo ln -s $PWD/supervisor.conf /etc/supervisor/conf.d/wsn.conf
  $ sudo supervisorctl reread
  $ sudo supervisorctl update


RabbitMQ: Plugins
=================

List plugins::

  # rabbitmq-plugins list

Example, the management plugin::

  # rabbitmq-plugins enable rabbitmq_management

With the management plugin enabled, you can:

- Go to http://localhost:15672/ and enter with username and password "guest".
- Use the command line rabbitmqadmin


RabbitMQ (command line)
=======================

::

  # rabbitmqctl list_exchanges
  # rabbitmqctl list_queues
  # rabbitmqctl list_bindings
  # rabbitmqctl list_connections

  # rabbitmqctl list_channels
  # rabbitmqctl list_consumers
  # rabbitmqctl status

TODO Document rabbitmqadmin


RabbitMQ: Federated Exchange (TODO)
===================================

Everything below is done in the server:

Enable federation plugin::

  # rabbitmq-plugins enable rabbitmq_federation
  # rabbitmq-plugins enable rabbitmq_federation_management

Define the upstream::

  # rabbitmqctl set_parameter federation-upstream finse_pi '{"uri":"amqp://129.240.244.148"}'
  # rabbitmqctl set_parameter federation-upstream cs_pi '{"uri":"amqp://192.168.1.133"}'

Verify::

  # rabbitmqctl list_parameters

Define a policy, and verify::

  # rabbitmqctl set_policy --apply-to exchanges wsn "^wsn$" '{"federation-upstream-set":"all"}'
  # rabbitmqctl list_policies
  # rabbitmqctl eval 'rabbit_federation_status:status().'
