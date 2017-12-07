Install
=======

Install system wide requirements::

  $ sudo apt-get install python3-venv
  $ sudo apt-get install rabbitmq-server
  $ sudo apt-get install supervisor

Build::

  $ make install

Create a symbolic link, as root, to the supervisor configuration::

  $ sudo ln -s $PWD/supervisor.conf /etc/supervisor/conf.d/wsn.conf
  $ supervisorctl reread
  $ supervisorctl update


RabbitMQ plugins
================

::

  # rabbitmq-plugins list
  # rabbitmq-plugins enable rabbitmq_management

Go to http://localhost:15672/ and enter with username and password "guest".
