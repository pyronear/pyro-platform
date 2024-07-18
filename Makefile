# this target runs checks on all files
quality:
	ruff check .
	mypy
	black --check .
	bandit -r . -c pyproject.toml

# this target runs checks on all files and potentially modifies some of them
style:
	black .
	ruff --fix .

# Build the docker
build:
	poetry export -f requirements.txt --without-hashes --output requirements.txt
	docker build . -t pyronear/pyro-platform:latest
	
# Run the docker for production
run:
	poetry export -f requirements.txt --without-hashes --output requirements.txt
	docker compose -f docker-compose.yml up -d --build

# Run the docker for dev purposes
run_dev:
	poetry export -f requirements.txt --without-hashes --output requirements.txt
	docker compose -f docker-compose-dev.yml up -d --build

run_local:
	python app/index.py --host 0.0.0.0 --port 8050

# Run the docker
stop:
	docker compose down

# Pin the dependencies
lock:
	poetry lock -vvv
