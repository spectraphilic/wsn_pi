.PHONY: etc install

install:
	python3 -m venv venv
	./venv/bin/pip install -U pip
	./venv/bin/pip install -r requirements.txt
	mkdir -p etc
	mkdir -p log
	mkdir -p var
	./venv/bin/python etc.py

etc:
	./venv/bin/python etc.py
