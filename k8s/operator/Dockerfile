FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir kopf[full]==1.37.2 kubernetes==29.0.0

COPY operator.py /app/operator.py

ENV PYTHONUNBUFFERED=1

CMD ["kopf", "run", "--standalone", "--verbose", "/app/operator.py"]
