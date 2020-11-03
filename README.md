# Pyronear WebApp
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE) [![Codacy Badge](https://app.codacy.com/project/badge/Grade/0e4490e06eaf41a3a5faea69dad5caa9)](https://www.codacy.com/gh/pyronear/pyronear-webapp/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=pyronear/pyronear-webapp&amp;utm_campaign=Badge_Grade) ![Build Status](https://github.com/pyronear/pyronear-webapp/workflows/dash-project/badge.svg) 

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
git clone https://github.com/pyronear/pyronear-webapp.git
pip install -r pyronear-webapp/requirements.txt
```



## Usage

#### Plain dash server

You can run the web server using the following commands:

```bash
cd app
python main.py
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
