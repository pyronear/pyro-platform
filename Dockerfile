FROM python:3.7.9-slim

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# copy requirements file
COPY ./requirements.txt /usr/src/app/requirements.txt

# install dependencies
RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && pip install --upgrade pip setuptools wheel \
    && pip install -r /usr/src/app/requirements.txt \
    && apt-get purge --autoremove -y git \
    && rm -rf /root/.cache/pip \
    && rm -rf /var/lib/apt/lists/*

# copy project
COPY app/ /usr/src/app/
