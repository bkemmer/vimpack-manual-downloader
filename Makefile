test:
	python3 -m pytest

lint:
	python3 -m ruff check

format:
	python3 -m ruff format

install-dev-requirements:
	python3 -m pip install -r requirements-dev.txt
