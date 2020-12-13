# Pyronear Platform
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE) [![Codacy Badge](https://app.codacy.com/project/badge/Grade/0e4490e06eaf41a3a5faea69dad5caa9)](https://www.codacy.com/gh/pyronear/pyro-platform/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=pyronear/pyro-platform&amp;utm_campaign=Badge_Grade) ![Build Status](https://github.com/pyronear/pyro-platform/workflows/dash-project/badge.svg) 

The building blocks of our wildfire detection & monitoring API.



## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [License](#license)



## Getting started

### Prerequisites

- Python 3.6 (or more recent)
- [pip](https://pip.pypa.io/en/stable/)

### Installation

You can clone and install the project dependencies as follows:

```bash
git clone https://github.com/pyronear/pyro-platform.git
pip install -r pyro-platform/requirements.txt
```



## Usage

Beforehand, you will need to set a few environment variables either manually or by writing an `.env` file in the root directory of this project, like in the example below:

```
API_URL=http://my-api.myhost.com
API_LOGIN=my_secret_login
API_PWD=my_very_secret_password

```
Those values will allow your web server to connect to our [API](https://github.com/pyronear/pyro-api), which is mandatory for your local server to be fully operational.

#### Plain dash server

You can run the web server using the following commands:

```bash
python app/main.py
```

Then your Dash app will be available at http://localhost:8050/

#### Dockerized dash server

If you wish to deploy this project on a server hosted remotely, you might want to be using [Docker](https://www.docker.com/) containers. You can perform the same using this command:

```bash
docker-compose up -d --build
```

Like previously, you can navigate then to http://localhost:8050/ to interact with your Dash app.



## License

Distributed under the GPLv3 License. See `LICENSE` for more information.
