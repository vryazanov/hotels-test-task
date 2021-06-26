FROM python:3.9-slim

RUN pip install poetry

COPY poetry.lock pyproject.toml /app/
WORKDIR /app

RUN poetry config virtualenvs.create false
RUN poetry install --no-root

COPY . /app
