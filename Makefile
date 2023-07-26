# this target runs checks on all files
quality:
	isort . -c
	flake8
	mypy
	black --check .
	bandit -r . -c pyproject.toml
	autoflake -r .

# this target runs checks on all files and potentially modifies some of them
style:
	isort .
	black .
	autoflake --in-place -r .

# Build the docker
build:
	poetry export -f requirements.txt --without-hashes --output requirements.txt
	docker build . -t pyronear/pyro-platform:python3.7.9-slim

# Run the docker for production
run:
	poetry export -f requirements.txt --without-hashes --output requirements.txt
	docker-compose -f docker-compose.yml up -d --build

# Run the docker for dev purposes
run_dev:
	poetry export -f requirements.txt --without-hashes --output requirements.txt
	docker-compose -f docker-compose-dev.yml up -d --build

# Run the docker
stop:
	docker-compose down

# Pin the dependencies
lock:
	poetry lock -vvv
