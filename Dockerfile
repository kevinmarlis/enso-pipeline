FROM python:3.9.13-slim-buster

RUN apt-get update \
    && apt-get install -y gcc build-essential python3-dev libgeos-dev \
    && apt-get install -y wget python3-pip vim\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD [ "python", "run_pipeline" ]