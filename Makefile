install:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	mkdir -p log
	mkdir -p var
	bash supervisor.sh > supervisor.conf
