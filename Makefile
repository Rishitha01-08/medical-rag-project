.PHONY: setup test lint format format-check typecheck run docker-up docker-down evaluate

setup:
	python -m pip install -r requirements.txt

test:
	MOCK_MODE=true pytest

lint:
	ruff check app tests scripts evaluation

format:
	ruff format app tests scripts evaluation

format-check:
	ruff format --check app tests scripts evaluation

typecheck:
	mypy app

run:
	MOCK_MODE=true uvicorn app.main:app --reload

docker-up:
	docker compose up --build

docker-down:
	docker compose down

evaluate:
	MOCK_MODE=true python -m evaluation.run_evaluation
