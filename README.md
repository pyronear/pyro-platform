# Pyronear Platform
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE) [![Codacy Badge](https://app.codacy.com/project/badge/Grade/0e4490e06eaf41a3a5faea69dad5caa9)](https://www.codacy.com/gh/pyronear/pyro-platform/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=pyronear/pyro-platform&amp;utm_campaign=Badge_Grade) ![Build Status](https://github.com/pyronear/pyro-platform/workflows/dash-project/badge.svg)

The open-source platform for managing early wildfire detection


# Installation

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/)
- [Docker compose](https://docs.docker.com/compose/)
- [Poetry](https://python-poetry.org/)
- [Make](https://www.gnu.org/software/make/) (optional)

The project was designed so that everything runs with Docker orchestration (standalone virtual environment), so you won't need to install any additional libraries.

## Configuration

In order to run the project, you will need to specific some information, which can be done using a `.env` file.

This file will have to hold the following information:
- `API_URL`: URL to the endpoint of [Pyronear Alert API](https://github.com/pyronear/pyro-api)
- `API_LOGIN`: your login for the API
- `API_PWD`: your password for the API

Optionally, the following information can be added:
- `SENTRY_DSN`: the URL of the [Sentry](https://sentry.io/) project, which monitors back-end errors and report them back.
- `SENTRY_SERVER_NAME`: the server tag to apply to events.
- `DEBUG`: whether the app is in debug or production mode

So your `.env` file should look like something similar to:
```
API_URL='https://alert.mydomain.com/api'
API_LOGIN='forest_saver'
API_PWD='ILoveForest!'
SENTRY_DSN='https://replace.with.you.sentry.dsn/'
SENTRY_SERVER_NAME=my_storage_bucket_name
```

The file should be placed at the root folder of your local copy of the project.


## Running you service locally

### Clone the repository
```shell
git clone https://github.com/pyronear/pyro-platform.git && cd pyro-platform
```

Here, there are several ways to start the service
- Either you have access to a pyronear alert api online through a specific API_URL
- Otherwise, you'll need to create a development environment. Don't panic, here's a tutorial on how to do it smoothly

### Run the service directly with the URL of a pyronear alert api

#### 1 - Set your environment variables 
First copy the example environment setup
```shell
cp .env.example .env
```
Fill it with your API_URL and credentials

#### 2 - You can run the app container using this command for dev purposes:
```shell
make run_dev
```

### Run the service via a development environment

#### 1 - clone pyro-envdev repository 
Move to a directoty where to clone the [pyro-envdev repo](https://github.com/pyronear/pyro-envdev), then

```shell
git clone https://github.com/pyronear/pyro-envdev.git && cd pyro-envdev
```

#### 2 - build & launch required pyro-envdev services
```shell
make build
```
Then, with the following command, you will run the API locally and services that simulate 2 cameras generating alerts

```shell
make run-engine
```
### 3 - Let your webbrowser access images from development environment
by adding this line in your /etc/hosts

```
127.0.0.1 www.localstack.com localstack
```

#### 4 - Go back to pyro-platform & setup credentials
```shell
cd PATH_TO_PYRO-PLATFORM
```

Fill credentials to access your local API, the example below shall work properly as the API_URL give access to your local pyronear api and (API_LOGIN, API_PWD) are taken from [default credentials in the development environment](https://github.com/pyronear/pyro-envdev/blob/main/data/csv/API_DATA_DEV%20-%20users.csv)

```
API_URL='http://host.docker.internal:5050/'
API_LOGIN='github-engine'
API_PWD='passwrd6'
```

### 4 - Start your local pyro-plateform 

Now, you can run the app container using this command for dev purposes:

```shell
make run_dev
```

or launch your project locally directly with python: 

```shell
python3 app/index.py
```

### Check how what you've deployed

You can now navigate to `http://localhost:8050/` to interact with the app.

In order to stop the service, run:
```shell
make stop
```


## Running your service in production

```shell
make run
```

For production we use docker-compose.yml in which there is the [Traefik Reverse Proxy](https://traefik.io/traefik/).

Traefik interacts with the Dash frontend app via an external network called web, this needs do be created as follow:

```shell
docker network create web
```

## Contributing

Any sort of contribution is greatly appreciated!

You can find a short guide in [`CONTRIBUTING`](CONTRIBUTING.md) to help grow this project!


## License

Distributed under the Apache 2.0 License. See `LICENSE` for more information.
