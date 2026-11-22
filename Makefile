.PHONY: install run demo test lint docker

install:
	pip install -r requirements-dev.txt

run:
	streamlit run app.py

demo:
	SNAP_DEMO_MODE=1 streamlit run app.py

test:
	pytest

lint:
	ruff check . && ruff format --check .

docker:
	docker compose up --build
