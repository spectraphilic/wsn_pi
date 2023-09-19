.PHONY: ctl etc install start stop

CONFIG=var/supervisor.conf


ctl:
	./venv/bin/supervisorctl -c ${CONFIG}

start:
	./venv/bin/supervisord -c ${CONFIG} -n

stop:
	kill -TERM `cat var/run/supervisord.pid`

tree:
	mkdir -p log
	mkdir -p var/log
	mkdir -p var/run

etc: tree
	./venv/bin/python etc.py

install: tree
	python3 -m venv venv
	./venv/bin/pip install -U pip
	./venv/bin/pip install -r requirements.txt
