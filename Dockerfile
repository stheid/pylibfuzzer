FROM python:slim

WORKDIR /code
COPY . .
RUN pip install .

ENTRYPOINT python pylibfuzzer/exec/runner.py