# this target runs checks on all files
quality:
	isort . -c
	flake8
	mypy
	black --check .

# this target runs checks on all files and potentially modifies some of them
style:
	isort .
	black .

# Build the docker
build:
	poetry export -f requirements.txt --without-hashes --output requirements.txt
	docker build . -t pyroplatform:python3.7.9-slim

# Run the docker
run:
	poetry export -f requirements.txt --without-hashes --output requirements.txt
	docker-compose up -d --build

# Run the docker
stop:
	docker-compose down

# Pin the dependencies
lock:
	poetry lock -vvv
