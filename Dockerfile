FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

COPY . .
RUN mkdir -p /app/instance /app/uploads /app/logs

EXPOSE 8362

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8362", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
