install:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	mkdir -p log
	mkdir -p var
	./venv/bin/python supervisor.py > supervisor.conf
