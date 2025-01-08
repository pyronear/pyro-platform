FROM python:3.9-slim

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# copy pyproject file to generate requirements.txt
ADD ./pyproject.toml /tmp/pyproject.toml

# install dependencies
WORKDIR /tmp
RUN apt update \
    && apt install git -y \
    && pip install --upgrade pip setuptools wheel \
    && pip install  --root-user-action ignore poetry \
    && poetry export -f requirements.txt --without-hashes --output ./requirements.txt \
    && pip install -r ./requirements.txt \
    && rm -rf /root/.cache/pip \
    && apt purge git -y

# copy project
ADD app/ /usr/src/app/

WORKDIR /usr/src/app
CMD python index.py --host 0.0.0.0 --port 8050