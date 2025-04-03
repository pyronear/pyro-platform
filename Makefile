# This target runs checks on all files
quality:
	ruff check .
	mypy

# This target auto-fixes lint issues where possible
style:
	ruff format .
	ruff check --fix .

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

# Run the docker
stop:
	docker compose down

# Pin the dependencies
lock:
	poetry lock -vvv
