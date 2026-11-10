.PHONY: test integration lint build offline baseline delay
test:
	uv run pytest -q -m 'not integration'
integration:
	TWIN_RUN_INTEGRATION=1 uv run pytest -q
lint:
	uv run ruff check src tests notebooks scripts kit
build:
	uv build --wheel
offline:
	python scripts/prepare_offline.py
baseline:
	uv run airport-twin run --scenario baseline --seed 42
delay:
	uv run airport-twin run --scenario delay_A4 --seed 42
