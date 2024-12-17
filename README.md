# Pyronear Platform
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE) [![Codacy Badge](https://app.codacy.com/project/badge/Grade/0e4490e06eaf41a3a5faea69dad5caa9)](https://www.codacy.com/gh/pyronear/pyro-platform/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=pyronear/pyro-platform&amp;utm_campaign=Badge_Grade) ![Build Status](https://github.com/pyronear/pyro-platform/workflows/dash-project/badge.svg)

The building blocks of our wildfire detection & monitoring API.


## Quick Tour
### Pyro API
1. Hosted by pyronear
You can use apidev.pyronear.org/docs if you don't need to modify the API for your task

What to do : 
=> you need to ask an administrator to create a user for you. Better to have an admin user in order to be able to create cameras & detections with it.
=> check that the version of the dev API will be fitter to your need.
=> modify the API_URL var env in your .env

2. Locally
You can use the pyro-devops project in two different ways :
=> by building the pyro-platform image and launch the full development environment with the command :
```shell
make run
```
=> by launching the development environment without the platform :
```shell
make run-engine
```
adding this line in your /etc/hosts :
```
127.0.0.1 www.localstack.com localstack
```
after that you can set up the .env of the pyro-platform project according to the values contained in the .env of the pyro-devops project 
And launch your project according to the section below "Directly in python" 



### Running/stopping the service
1. Dockerized
You can run the app container using this command for dev purposes:

```shell
make run_dev
```

or for production:

```shell
make run
```

You can now navigate to `http://localhost:8050/` to interact with the app.

In order to stop the service, run:
```shell
make stop
```

This dockerized setup won't work with an API launch thanks to the pyro-devops projet

2. Directly in python
Set up your .env

```shell
pip install -r requirements.txt
pip install --no-cache-dir git+https://github.com/pyronear/pyro-api.git@ce7bf66d1624fcb615daee567dfa77d7d5bca487#subdirectory=client
python app/index.py --host 0.0.0.0 --port 8050
```

## Installation

### Prerequisites

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

Also please note that you should use docker-compose-dev.yml file for dev as we do not need reverse proxy:

```shell
docker-compose -f docker-compose-dev.yml up
```

For production we use docker-compose.yml in which there is the [Traefik Reverse Proxy](https://traefik.io/traefik/).

Traefik interacts with the Dash frontend app via an external network called web, this needs do be created as follow:

```shell
docker network create web
```


## License

Distributed under the Apache 2.0 License. See `LICENSE` for more information.
