FROM python:3.8-slim-buster

RUN apt update && apt -y install cron

WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY crontab /etc/cron.d/sync
RUN chmod 644 /etc/cron.d/sync && crontab /etc/cron.d/sync

COPY sync.py /app

CMD cron -f
