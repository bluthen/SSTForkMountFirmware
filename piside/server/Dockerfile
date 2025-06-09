FROM python:3.11-slim

RUN apt update && apt upgrade -y && apt clean
RUN apt install socat python3-pip libblas3 liblapack3 libatlas3-base ntpdate ntpstat avahi-utils astrometry.net imagemagick libssl-dev libbz2-dev libncurses-dev libreadline-dev libffi-dev libsqlite3-dev lzma-dev -y && apt clean
RUN apt install procps -y && apt clean
RUN pip install poetry
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_HOME=/opt/poetry
RUN mkdir -p /workspace/server
RUN mkdir -p /workspace/client_advanced_slew_limits
WORKDIR /workspace/server
ADD poetry.lock /workspace/server/
ADD poetry.toml /workspace/server/
ADD pyproject.toml /workspace/server

RUN poetry install --no-interaction --no-ansi

